
import os
import json
from typing import List, Optional, Union
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
import fitz  # PyMuPDF
import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# Load environment variables from .env file
load_dotenv()

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

# --- FastAPI Application ---

app = FastAPI()

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


@app.post("/parse-resume/", response_model=Resume)
async def parse_resume(file: UploadFile = File(...)):
    """
    Upload a resume in PDF format, parse it, and return structured JSON data.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # 1. Extract text from the PDF
        resume_text = extract_text_from_pdf(file_path)
        
        # Debug: log extracted text
        print(f"Extracted text length: {len(resume_text)}")
        print(f"First 500 chars: {resume_text[:500]}...")
        
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
        except Exception as validation_error:
            # Log the validation error and the parsed data for debugging
            print(f"Validation error: {validation_error}")
            print(f"Parsed data: {parsed_data}")
            
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

        return resume

    except HTTPException as e:
        raise e
    except Exception as e:
        # Log the error for debugging
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



