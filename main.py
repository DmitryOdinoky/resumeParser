
import os
import json
import tempfile
import uuid
from io import BytesIO
from typing import List, Optional, Union
from datetime import timedelta
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
import fitz  # PyMuPDF
import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from minio import Minio
from minio.error import S3Error
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MinIO Configuration ---
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
INPUT_BUCKET = os.getenv("INPUT_BUCKET", "input-resumes")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET", "output-json")

# Initialize MinIO client
try:
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )
    logger.info(f"MinIO client initialized: {MINIO_ENDPOINT}")
except Exception as e:
    logger.error(f"Failed to initialize MinIO client: {e}")
    minio_client = None

# --- Pydantic Models for Resume Structure ---

class Education(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    from_date: Optional[str] = Field(None, alias="from")
    to_date: Optional[str] = Field(None, alias="to")
    ongoing: bool = False
    grade: Optional[str] = None

class Certificate(BaseModel):
    title: str
    from_date: Optional[str] = Field(None, alias="from")
    to_date: Optional[str] = Field(None, alias="to")
    ongoing: bool = False
    path: Optional[str] = None

class Experience(BaseModel):
    industry: str
    position: str
    from_date: Optional[str] = Field(None, alias="from")
    to_date: Optional[str] = Field(None, alias="to")
    ongoing: bool = False
    description: Optional[str] = None

class Language(BaseModel):
    language: str
    level: str

class Reference(BaseModel):
    name: str
    position: Optional[str] = None
    company: Optional[str] = None
    mobile: Optional[str] = None
    path: Optional[str] = None

class Resume(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    country: Optional[str] = None
    industry: List[str] = []
    positions: List[str] = []
    contract: Optional[str] = None
    education: List[Education] = []
    certificates: List[Certificate] = []
    experience: List[Experience] = []
    languages: List[Language] = []
    extra_skills: List[str] = []
    references: List[Reference] = []

    # Removed industry validation to allow any industry

    @field_validator('languages')
    def validate_languages(cls, v):
        allowed_levels = {"native", "fluent", "intermediate", "beginner"}
        for lang in v:
            if lang.level not in allowed_levels:
                raise ValueError(f"Language level '{lang.level}' is not allowed.")
        return v

# --- MinIO Helper Functions ---

def ensure_buckets_exist():
    """Ensure that required MinIO buckets exist"""
    if not minio_client:
        return False
    
    try:
        for bucket in [INPUT_BUCKET, OUTPUT_BUCKET]:
            if not minio_client.bucket_exists(bucket):
                minio_client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")
            else:
                logger.info(f"Bucket already exists: {bucket}")
        return True
    except S3Error as e:
        logger.error(f"Error creating buckets: {e}")
        return False

def upload_to_minio(file_data: bytes, object_name: str, bucket: str, content_type: str = "application/octet-stream"):
    """Upload file data to MinIO bucket"""
    if not minio_client:
        raise HTTPException(status_code=500, detail="MinIO client not available")
    
    try:
        minio_client.put_object(
            bucket,
            object_name,
            BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
        logger.info(f"Uploaded {object_name} to {bucket}")
        return True
    except S3Error as e:
        logger.error(f"Error uploading to MinIO: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")

def download_from_minio(object_name: str, bucket: str) -> bytes:
    """Download file data from MinIO bucket"""
    if not minio_client:
        raise HTTPException(status_code=500, detail="MinIO client not available")
    
    try:
        response = minio_client.get_object(bucket, object_name)
        return response.read()
    except S3Error as e:
        logger.error(f"Error downloading from MinIO: {e}")
        raise HTTPException(status_code=404, detail=f"File not found: {e}")
    finally:
        if 'response' in locals():
            response.close()
            response.release_conn()

def get_file_url(object_name: str, bucket: str) -> str:
    """Get presigned URL for file in MinIO"""
    if not minio_client:
        return f"http://{MINIO_ENDPOINT}/{bucket}/{object_name}"
    
    try:
        # Generate presigned URL (valid for 7 days)
        url = minio_client.presigned_get_object(bucket, object_name, expires=timedelta(days=7))
        return url
    except S3Error as e:
        logger.error(f"Error generating URL: {e}")
        return f"http://{MINIO_ENDPOINT}/{bucket}/{object_name}"

# --- FastAPI Application ---

app = FastAPI(
    title="Resume Parser API",
    description="AI-powered resume parsing service with OCR support and MinIO storage",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Resume Parser API...")
    if minio_client:
        ensure_buckets_exist()
    else:
        logger.warning("MinIO client not available - falling back to local storage")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "minio_available": minio_client is not None,
        "buckets": {
            "input": INPUT_BUCKET,
            "output": OUTPUT_BUCKET
        }
    }

# --- Google Gemini Client ---
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file.")

genai.configure(api_key=api_key)

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts text from a PDF file. Uses OCR if regular text extraction fails."""
    try:
        # First, try regular text extraction with PyMuPDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # If no text was extracted, try OCR
        if len(text.strip()) == 0:
            print(f"No text extracted with PyMuPDF, trying OCR...")
            try:
                # Convert PDF to images
                images = convert_from_path(file_path, dpi=300)  # Higher DPI for better OCR
                
                # Process each page with OCR
                for i, image in enumerate(images):
                    page_text = pytesseract.image_to_string(image)
                    if page_text:
                        text += page_text + "\n"
                    print(f"OCR Page {i+1}: Extracted {len(page_text)} characters")
                
                if len(text.strip()) == 0:
                    print("OCR also failed to extract text")
                else:
                    print(f"OCR successfully extracted {len(text)} characters")
                    
            except Exception as ocr_error:
                print(f"OCR error: {ocr_error}")
                # If OCR also fails, return empty string
                text = ""
        
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {e}")

async def parse_resume_with_ai(text: str) -> dict:
    """
    Uses Google Gemini to parse the resume text and return structured JSON.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    system_prompt = """
    You are an expert resume parser. Your task is to analyze the provided resume text
    and extract the ACTUAL information from the resume into a structured JSON object. 
    
    IMPORTANT: 
    - Extract REAL data from the resume, NOT placeholder or example data
    - Pay close attention to the actual name, contact details, and experience mentioned in the CV
    - Look for language abbreviations (EN=English, DE=German, ES=Spanish, etc.)
    - Skills might be mentioned in experience descriptions and certifications
    - If language is not mentioned, include the nationality-related language
    
    Return a JSON object with the following structure:
    {
        "full_name": "Actual person's name from CV",
        "phone": "Phone number if found",
        "email": "Email address if found",
        "country": "Country if mentioned",
        "industry": ["List of relevant industries based on experience"],
        "positions": ["List of job positions/titles"],
        "contract": "Contract type if mentioned",
        "education": [
            {
                "institution": "University/School name",
                "degree": "Degree type (Bachelor, Master, PhD, etc.)",
                "field_of_study": "Field of study/Major",
                "from": "Start date YYYY-MM-DD",
                "to": "End date YYYY-MM-DD or null if ongoing",
                "ongoing": true/false,
                "grade": "GPA/Grade if mentioned"
            }
        ],
        "certificates": [
            {
                "title": "Certificate name",
                "from": "Start date YYYY-MM-DD",
                "to": "End date YYYY-MM-DD",
                "ongoing": false,
                "path": "URL or path if mentioned"
            }
        ],
        "experience": [
            {
                "industry": "Industry name",
                "position": "Job title",
                "from": "Start date YYYY-MM-DD",
                "to": "End date YYYY-MM-DD or null if current",
                "ongoing": true/false,
                "description": "Job description"
            }
        ],
        "languages": [
            {
                "language": "Language name",
                "level": "native/fluent/intermediate/beginner"
            }
        ],
        "extra_skills": ["List of technical skills"],
        "references": [
            {
                "name": "Reference name",
                "position": "Their position",
                "company": "Their company",
                "mobile": "Phone number",
                "path": "URL or path"
            }
        ]
    }

    Important Rules:
    - Extract the actual person's name from the CV, NOT "John Smith" or any placeholder
    - For industries, use relevant terms like 'technology', 'music', 'engineering', 'research', etc.
    - For education: Look for universities, colleges, schools, degrees (Bachelor, Master, PhD, MSc, BSc, etc.), graduation years, fields of study
    - Languages level must be: 'native', 'fluent', 'intermediate', or 'beginner'
    - Dates: Format as 'YYYY-MM-DD'. If only month/year, use first day (YYYY-MM-01). If only year, use January 1st.
    - If a field is not found, omit it or use empty array [] for lists
    - Your output must be ONLY the JSON object, no other text
    """
    
    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.1,  # Lower temperature for more consistent output
    )

    try:
        response = await model.generate_content_async(
            [system_prompt, text],
            generation_config=generation_config,
        )
        # Clean up the response to ensure it's valid JSON
        cleaned_response_text = response.text.strip()
        if cleaned_response_text.startswith("```json"):
            cleaned_response_text = cleaned_response_text[7:]
        if cleaned_response_text.endswith("```"):
            cleaned_response_text = cleaned_response_text[:-3]
        
        parsed_json = json.loads(cleaned_response_text)
        
        # Debug logging
        print(f"AI Response: {cleaned_response_text[:500]}...")  # First 500 chars
        
        return parsed_json
    except Exception as e:
        # This will catch errors from the API call or JSON decoding
        print(f"AI processing error: {e}")
        print(f"Raw response: {cleaned_response_text[:1000] if 'cleaned_response_text' in locals() else 'No response'}")
        raise HTTPException(status_code=502, detail=f"Error during AI processing: {e}")


@app.post("/parse-resume/")
async def parse_resume(file: UploadFile = File(...)):
    """
    Upload a resume in PDF format, parse it, and return structured JSON data with MinIO storage.
    Returns URLs to the stored files instead of inline data when MinIO is available.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    # Generate unique filename to avoid conflicts
    file_id = str(uuid.uuid4())
    original_filename = file.filename
    pdf_object_name = f"{file_id}_{original_filename}"
    json_object_name = f"{file_id}_{original_filename.replace('.pdf', '.json')}"
    
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, pdf_object_name)

    try:
        # Read file data
        file_data = await file.read()
        
        # Save temporarily for processing
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_data)

        # Store original PDF in MinIO if available
        if minio_client:
            upload_to_minio(file_data, pdf_object_name, INPUT_BUCKET, "application/pdf")
            logger.info(f"Uploaded PDF to MinIO: {pdf_object_name}")

        # 1. Extract text from the PDF
        resume_text = extract_text_from_pdf(temp_file_path)
        
        # Debug: log extracted text
        logger.info(f"Extracted text length: {len(resume_text)}")
        logger.info(f"First 500 chars: {resume_text[:500]}...")
        
        # Check if text was extracted
        if len(resume_text.strip()) == 0:
            raise HTTPException(
                status_code=400, 
                detail="No text could be extracted from the PDF. The file might be a scanned image or corrupted."
            )

        # 2. Parse the text with the AI model
        parsed_data = await parse_resume_with_ai(resume_text)

        # 3. Validate the data with the Pydantic model
        try:
            resume = Resume(**parsed_data)
            resume_dict = resume.model_dump()
        except Exception as validation_error:
            # Log the validation error and the parsed data for debugging
            logger.error(f"Validation error: {validation_error}")
            logger.error(f"Parsed data: {parsed_data}")
            
            # Try to provide a more helpful error message
            error_detail = str(validation_error)
            if "language level" in error_detail.lower():
                raise HTTPException(
                    status_code=422, 
                    detail=f"Invalid language level found. Allowed levels: native, fluent, intermediate, beginner. Error: {error_detail}"
                )
            else:
                raise HTTPException(
                    status_code=422, 
                    detail=f"Resume data validation failed: {error_detail}"
                )

        # 4. Store parsed JSON in MinIO if available
        if minio_client:
            json_data = json.dumps(resume_dict, indent=2, ensure_ascii=False).encode('utf-8')
            upload_to_minio(json_data, json_object_name, OUTPUT_BUCKET, "application/json")
            logger.info(f"Uploaded JSON to MinIO: {json_object_name}")
            
            # Return URLs to stored files
            return {
                "status": "success",
                "file_id": file_id,
                "original_filename": original_filename,
                "pdf_url": get_file_url(pdf_object_name, INPUT_BUCKET),
                "json_url": get_file_url(json_object_name, OUTPUT_BUCKET),
                "parsed_data": resume_dict
            }
        else:
            # Fallback: return inline data when MinIO is not available
            logger.warning("MinIO not available, returning inline data")
            return {
                "status": "success",
                "file_id": file_id,
                "original_filename": original_filename,
                "parsed_data": resume_dict,
                "note": "MinIO storage not available - data returned inline only"
            }

    except HTTPException as e:
        raise e
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/download/{bucket}/{object_name}")
async def download_file(bucket: str, object_name: str):
    """
    Download a file from MinIO storage
    """
    if bucket not in [INPUT_BUCKET, OUTPUT_BUCKET]:
        raise HTTPException(status_code=400, detail="Invalid bucket name")
    
    try:
        file_data = download_from_minio(object_name, bucket)
        
        # Determine content type based on file extension
        if object_name.endswith('.pdf'):
            content_type = "application/pdf"
        elif object_name.endswith('.json'):
            content_type = "application/json"
        else:
            content_type = "application/octet-stream"
            
        from fastapi.responses import Response
        return Response(
            content=file_data,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={object_name}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {e}")

@app.get("/files/{bucket}")
async def list_files(bucket: str):
    """
    List all files in a MinIO bucket
    """
    if bucket not in [INPUT_BUCKET, OUTPUT_BUCKET]:
        raise HTTPException(status_code=400, detail="Invalid bucket name")
    
    if not minio_client:
        raise HTTPException(status_code=503, detail="MinIO client not available")
    
    try:
        objects = minio_client.list_objects(bucket, recursive=True)
        files = []
        for obj in objects:
            files.append({
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
                "url": get_file_url(obj.object_name, bucket)
            })
        return {"bucket": bucket, "files": files}
    except S3Error as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



