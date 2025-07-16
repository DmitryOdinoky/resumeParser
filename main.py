
import os
import json
from typing import List, Optional, Union
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
import fitz  # PyMuPDF
import uvicorn
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Pydantic Models for Resume Structure ---

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
    certificates: List[Certificate] = []
    experience: List[Experience] = []
    languages: List[Language] = []
    extra_skills: List[str] = []
    references: List[Reference] = []

    @field_validator('industry')
    def validate_industry(cls, v):
        allowed_industries = {"wind", "oil_n_gas", "maritime"}
        for item in v:
            if item not in allowed_industries:
                raise ValueError(f"Industry '{item}' is not allowed.")
        return v

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
    """Extracts text from a PDF file."""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading PDF: {e}")

async def parse_resume_with_ai(text: str) -> dict:
    """
    Uses Google Gemini to parse the resume text and return structured JSON.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    system_prompt = f"""
    You are an expert resume parser. Your task is to analyze the provided resume text
    and extract the information into a structured JSON object. The JSON object must
    strictly adhere to the following Pydantic schema. Your output must be only the JSON object, with no other text or explanations.

    Schema:
    {Resume.model_json_schema()}

    Important Rules:
    - `industry`: Must be one of 'wind', 'oil_n_gas', or 'maritime'. If multiple are relevant, include them all. If none seem to fit, choose the closest one or make a reasonable guess based on the context.
    - `languages`: The 'level' must be one of 'native', 'fluent', 'intermediate', or 'beginner'. Map the candidate's description to one of these levels.
    - `experience`: 'ongoing' should be true if the end date is in the future, not specified, or listed as 'present' or 'current'.
    - Dates: Format all dates as 'YYYY-MM-DD'. If only month and year are provided, use the first day of the month (e.g., 'YYYY-MM-01').
    - If a field is not found in the resume, omit it from the JSON object.
    """
    
    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json",
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
        return parsed_json
    except Exception as e:
        # This will catch errors from the API call or JSON decoding
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

        # 2. Parse the text with the AI model
        parsed_data = await parse_resume_with_ai(resume_text)

        # 3. Validate the data with the Pydantic model
        resume = Resume(**parsed_data)

        return resume

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



