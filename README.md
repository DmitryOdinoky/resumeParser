# Resume Parser API

This project is a FastAPI application that parses resumes from PDF files and returns a structured JSON output using the Google Gemini API.

## Features

-   **PDF Processing**: Upload resumes in PDF format with support for both text-based and scanned PDFs
-   **OCR Support**: Automatically detects scanned PDFs and uses OCR (Optical Character Recognition) for text extraction
-   **AI-Powered Parsing**: Uses Google Gemini API to intelligently extract and structure resume information
-   **Comprehensive Data Extraction**: Extracts personal information, education, experience, certifications, languages, skills, and references
-   **Flexible Industry Classification**: No restrictions on industry types - supports any field
-   **Batch Processing**: Process multiple PDFs simultaneously
-   **Comprehensive Testing**: Includes unified test suite with colored output and detailed reporting

## Project Structure

```
.
├── input/                        # Directory for test PDF files (gitignored)
├── output/                       # Directory for JSON output (gitignored)
├── temp/                         # Temporary files directory (gitignored)
├── venv/                         # Python virtual environment (gitignored)
├── .env                          # For storing your API key (gitignored)
├── .gitignore                    # Git ignore rules
├── main.py                       # FastAPI application with OCR support
├── client.py                     # Single file test client
├── batch_client.py               # Batch processing test client
├── test_resume_parser.py         # Comprehensive testing suite
├── server.log                    # Application logs (gitignored)
├── README.md                     # This file
└── requirements.txt              # Python dependencies
```

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone git@github.com:DmitryOdinoky/resumeParser.git
    cd resumeParser
    ```

2.  **Create and activate the virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install system dependencies (for OCR support):**
    ```bash
    # On macOS (using Homebrew)
    brew install tesseract poppler
    
    # On Ubuntu/Debian
    sudo apt-get install tesseract-ocr poppler-utils
    
    # On Windows
    # Download and install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
    # Download and install Poppler from: https://blog.alivate.com.au/poppler-windows/
    ```

5.  **Set up your API Key:**
    This project uses the Google Gemini API. You must have an API key from Google AI Studio.

    -   Create a new file in the project's root directory named `.env`.
    -   Add the following line to the `.env` file, replacing `your_secret_api_key` with your actual key:
        ```
        GOOGLE_API_KEY='your_secret_api_key'
        ```
    The application will automatically load this key at startup. The `.env` file is included in `.gitignore`, so your key will not be committed to GitHub.

## How to Run

1.  **Start the FastAPI server:**
    ```bash
    uvicorn main:app --reload
    ```
    The application will be running at `http://127.0.0.1:8000`.

2.  **Test the application:**
    Use the comprehensive test suite:
    
    ```bash
    # Test a single file
    python test_resume_parser.py -f "path/to/resume.pdf"
    
    # Run batch processing on all files in input directory
    python test_resume_parser.py -b
    
    # Run comprehensive test (default)
    python test_resume_parser.py
    
    # Get help
    python test_resume_parser.py --help
    ```
    
    Or use the individual client scripts:

    -   **For a single file:**
        ```bash
        python client.py
        ```
    -   **For all files in the `input` directory:**
        ```bash
        python batch_client.py
        ```
    The scripts will process PDF(s) and save the JSON responses in the `output` directory.

## API Endpoint

### POST /parse-resume/

-   **Request:**
    -   `file`: A PDF file (supports both text-based and scanned PDFs).
-   **Response:**
    -   A JSON object with the parsed resume data.

## JSON Output Structure

The API returns a comprehensive JSON object with the following structure:

```json
{
    "full_name": "Candidate's full name",
    "phone": "Phone number",
    "email": "Email address",
    "country": "Country/Location",
    "industry": ["List of relevant industries"],
    "positions": ["List of job titles/positions"],
    "contract": "Contract type if mentioned",
    "education": [
        {
            "institution": "University/School name",
            "degree": "Degree type (Bachelor, Master, PhD, etc.)",
            "field_of_study": "Field of study/Major",
            "from": "Start date (YYYY-MM-DD)",
            "to": "End date (YYYY-MM-DD) or null if ongoing",
            "ongoing": true/false,
            "grade": "GPA/Grade if mentioned"
        }
    ],
    "certificates": [
        {
            "title": "Certificate name",
            "from": "Start date (YYYY-MM-DD)",
            "to": "End date (YYYY-MM-DD)",
            "ongoing": false,
            "path": "URL or path if mentioned"
        }
    ],
    "experience": [
        {
            "industry": "Industry name",
            "position": "Job title",
            "from": "Start date (YYYY-MM-DD)",
            "to": "End date (YYYY-MM-DD) or null if current",
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
    "extra_skills": ["List of technical and other skills"],
    "references": [
        {
            "name": "Reference name",
            "position": "Their position",
            "company": "Their company",
            "mobile": "Phone number",
            "path": "URL or email"
        }
    ]
}
```

## Key Features

### OCR Support
- Automatically detects scanned PDFs that contain no extractable text
- Uses Tesseract OCR to extract text from images
- Supports multi-page PDF processing
- Maintains high accuracy for various document qualities

### AI-Powered Extraction
- Uses Google Gemini API for intelligent data parsing
- Extracts actual information (no placeholder data)
- Handles multiple date formats and converts to standardized format
- Supports flexible industry classification
- Recognizes language abbreviations and skill variations

### Error Handling
- Clear error messages for different failure scenarios
- Graceful fallback from text extraction to OCR
- Validation error details for debugging
- Server health checks in test suite
