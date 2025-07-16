# Resume Parser API

This project is a FastAPI application that parses resumes from PDF files and returns a structured JSON output using the Google Gemini API.

## Features

-   Upload a resume in PDF format.
-   Extracts text from the PDF.
-   Uses the Google Gemini API to parse the text and extract key information.
-   Returns a structured JSON response.

## Project Structure

```
.
├── input/                # Directory for test PDF files (gitignored)
├── output/               # Directory for JSON output (gitignored)
├── venv/                 # Python virtual environment (gitignored)
├── .env                  # For storing your API key (gitignored)
├── .gitignore
├── main.py               # FastAPI application
├── client.py             # Single file test client
├── batch_client.py       # Batch processing test client
├── README.md
└── requirements.txt
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

4.  **Set up your API Key:**
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

2.  **Use the test clients:**
    In a separate terminal, you can run either of the client scripts:

    -   **For a single file:**
        ```bash
        python client.py
        ```
    -   **For all files in the `input` directory:**
        ```bash
        python batch_client.py
        ```
    The scripts will send the PDF(s) to the API and save the JSON responses in the `output` directory.

## API Endpoint

### POST /parse-resume/

-   **Request:**
    -   `file`: A PDF file.
-   **Response:**
    -   A JSON object with the parsed resume data.
