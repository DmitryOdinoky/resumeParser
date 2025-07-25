# Resume Parser API

This project is a FastAPI application that parses resumes from PDF files and returns a structured JSON output using the Google Gemini API. It supports both local deployment and Docker containerization with MinIO object storage.

## Features

-   **PDF Processing**: Upload resumes in PDF format with support for both text-based and scanned PDFs
-   **OCR Support**: Automatically detects scanned PDFs and uses OCR (Optical Character Recognition) for text extraction
-   **AI-Powered Parsing**: Uses Google Gemini API to intelligently extract and structure resume information
-   **Comprehensive Data Extraction**: Extracts personal information, education, experience, certifications, languages, skills, and references
-   **Flexible Industry Classification**: No restrictions on industry types - supports any field
-   **Cloud Storage**: MinIO integration for distributed file storage (Docker version)
-   **Batch Processing**: Process multiple PDFs simultaneously
-   **Comprehensive Testing**: Includes unified test suite with colored output and detailed reporting
-   **Docker Support**: Ready-to-deploy containerized version with docker-compose

## Project Structure

```
.
├── input/                        # Directory for test PDF files (gitignored)
├── output/                       # Directory for JSON output (gitignored)  
├── temp/                         # Temporary files directory (gitignored)
├── venv/                         # Python virtual environment (gitignored)
├── .env                          # For storing your API key (gitignored)
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── main.py                       # FastAPI application with OCR and MinIO support
├── client.py                     # Single file test client
├── batch_client.py               # Batch processing test client
├── test_resume_parser.py         # Comprehensive testing suite
├── Dockerfile                    # Docker container configuration
├── docker-compose.yml            # Docker Compose with MinIO
├── nginx.conf                    # Nginx configuration (optional)
├── server.log                    # Application logs (gitignored)
├── README.md                     # This file
└── requirements.txt              # Python dependencies
```

## Deployment Options

This project supports two deployment methods:
- **Local Development**: Direct Python installation for development and testing
- **Docker Production**: Containerized deployment with MinIO object storage for production use

### Option 1: Docker Deployment (Recommended for Production)

**Prerequisites:**
- Docker and Docker Compose installed on your system
- At least 2GB RAM available for containers

#### Quick Start

1. **Clone the repository:**
   ```bash
   git clone git@github.com:DmitryOdinoky/resumeParser.git
   cd resumeParser
   ```

2. **Switch to docker branch:**
   ```bash
   git checkout docker-version
   ```

3. **Set your Google API key and deploy:**
   
   **Option A: Direct environment variable (Recommended)**
   ```bash
   # Replace 'your_api_key_here' with your actual Google Gemini API key
   GOOGLE_API_KEY=your_api_key_here docker-compose up -d
   ```
   
   **Option B: Using .env file**
   ```bash
   cp .env.example .env
   # Edit .env file with your Google API key
   nano .env  # or use your preferred editor
   docker-compose up -d
   ```

4. **Verify deployment:**
   ```bash
   # Check service status
   docker-compose ps
   
   # Test health endpoint
   curl http://localhost:8000/health
   
   # View logs if needed
   docker-compose logs -f resume-parser
   ```

#### Services Overview

The Docker deployment includes:

- **resume-parser** (Port 8000): Main FastAPI application
- **minio** (Port 9000): Object storage for files
- **minio-console** (Port 9001): MinIO web interface  
- **nginx** (Port 80/443): Reverse proxy (optional, for production)

#### Platform-Specific Instructions

**Linux (Ubuntu/Debian):**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again, then deploy
git checkout docker-version
GOOGLE_API_KEY=your_api_key_here docker-compose up -d
```

**macOS:**
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Or using Homebrew:
brew install --cask docker

# Deploy the application
git checkout docker-version
GOOGLE_API_KEY=your_api_key_here docker-compose up -d
```

**Windows:**
```powershell
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Open PowerShell as Administrator and run:

git checkout docker-version
$env:GOOGLE_API_KEY="your_api_key_here"; docker-compose up -d
```

#### Accessing Services

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (admin/password123)
- **File Upload**: POST http://localhost:8000/parse-resume/

#### Environment Variables

You can configure the application using either environment variables or a `.env` file:

**Method 1: Direct environment variables (Recommended)**
```bash
# Set variables directly when running docker-compose
GOOGLE_API_KEY=your_api_key_here \
MINIO_ROOT_PASSWORD=your_secure_password123 \
docker-compose up -d
```

**Method 2: Using .env file**
```bash
# Create .env file from template
cp .env.example .env
# Edit the file with your values
```

**Available Configuration Variables:**
```bash
# REQUIRED: Google Gemini API Key
# Get your key from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# MinIO Configuration
MINIO_ROOT_USER=admin                    # Default: admin
MINIO_ROOT_PASSWORD=password123          # Change for production!

# Application Settings
APP_HOST=0.0.0.0                        # Default: 0.0.0.0
APP_PORT=8000                           # Default: 8000

# Storage Buckets
INPUT_BUCKET=input-resumes              # Default: input-resumes
OUTPUT_BUCKET=output-json               # Default: output-json

# Production Settings
# MINIO_SECURE=true                     # Enable HTTPS for MinIO
```

#### Docker Management Commands

```bash
# Start services with environment variable
GOOGLE_API_KEY=your_api_key_here docker-compose up -d

# Start services (if using .env file)
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service-name]
docker-compose logs -f resume-parser  # Application logs
docker-compose logs -f minio          # MinIO storage logs

# Rebuild after code changes
docker-compose build --no-cache
GOOGLE_API_KEY=your_api_key_here docker-compose up -d

# Access service shell
docker-compose exec resume-parser bash

# Clean up everything (removes data!)
docker-compose down -v --remove-orphans

# Scale the application (multiple instances)
GOOGLE_API_KEY=your_api_key_here docker-compose up -d --scale resume-parser=3
```

### Option 2: Local Development Setup

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

## API Endpoints

### POST /parse-resume/

Upload and parse a resume PDF file.

-   **Request:**
    -   `file`: A PDF file (supports both text-based and scanned PDFs)
-   **Response (Docker with MinIO):**
    ```json
    {
        "status": "success",
        "file_id": "uuid-generated-id",
        "original_filename": "resume.pdf",
        "pdf_url": "http://localhost:9000/input-resumes/uuid_resume.pdf",
        "json_url": "http://localhost:9000/output-json/uuid_resume.json",
        "parsed_data": { /* structured resume data */ }
    }
    ```
-   **Response (Local mode):**
    ```json
    {
        "status": "success", 
        "file_id": "uuid-generated-id",
        "original_filename": "resume.pdf",
        "parsed_data": { /* structured resume data */ },
        "note": "MinIO storage not available - data returned inline only"
    }
    ```

### GET /health

Health check endpoint that shows system status.

-   **Response:**
    ```json
    {
        "status": "healthy",
        "minio_available": true,
        "buckets": {
            "input": "input-resumes",
            "output": "output-json"
        }
    }
    ```

### GET /files/{bucket}

List all files in a MinIO bucket (Docker version only).

-   **Parameters:**
    -   `bucket`: Either "input-resumes" or "output-json"
-   **Response:**
    ```json
    {
        "bucket": "input-resumes",
        "files": [
            {
                "name": "uuid_resume.pdf",
                "size": 1024576,
                "last_modified": "2024-01-01T12:00:00Z",
                "url": "http://localhost:9000/input-resumes/uuid_resume.pdf"
            }
        ]
    }
    ```

### GET /download/{bucket}/{object_name}

Download a file from MinIO storage (Docker version only).

-   **Parameters:**
    -   `bucket`: Either "input-resumes" or "output-json" 
    -   `object_name`: The file name to download
-   **Response:** File download with appropriate content-type headers

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

## Docker Production Deployment

For production deployment with SSL and domain configuration:

1. **Create nginx.conf:**
   ```bash
   # Create nginx configuration for production
   cat > nginx.conf << 'EOF'
   events {
       worker_connections 1024;
   }
   
   http {
       upstream resume-parser {
           server resume-parser:8000;
       }
       
       server {
           listen 80;
           server_name your-domain.com;
           
           location / {
               proxy_pass http://resume-parser;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
           
           client_max_body_size 10M;
       }
   }
   EOF
   ```

2. **Deploy with nginx:**
   ```bash
   docker-compose --profile production up -d
   ```

## Troubleshooting

### Common Issues

**Docker containers not starting:**
```bash
# Check Docker daemon
sudo systemctl status docker

# Check container logs
docker-compose logs

# Recreate containers
docker-compose down && docker-compose up -d
```

**MinIO connection issues:**
```bash
# Check MinIO container status
docker-compose ps minio

# Check MinIO logs
docker-compose logs minio

# Restart MinIO
docker-compose restart minio
```

**API returning 500 errors:**
```bash
# Check application logs
docker-compose logs resume-parser

# Common causes:
# - Missing GOOGLE_API_KEY in .env
# - Invalid Google API key
# - OCR dependencies missing (should be in Docker image)
```

**File upload failures:**
```bash
# Check disk space
df -h

# Check MinIO bucket permissions
docker-compose exec minio-init mc ls minio/
```

### Performance Tuning

For high-volume processing:

1. **Increase container resources:**
   ```yaml
   # In docker-compose.yml
   resume-parser:
     deploy:
       resources:
         limits:
           cpus: '2.0'
           memory: 4G
   ```

2. **Scale horizontally:**
   ```bash
   docker-compose up -d --scale resume-parser=3
   ```

### Security Considerations

- Change default MinIO credentials in production
- Use HTTPS in production (configure SSL certificates)
- Implement API rate limiting
- Regular security updates of base images
- Network isolation using Docker networks

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with detailed description

## License

This project is licensed under the MIT License - see the LICENSE file for details.
