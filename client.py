

import requests
import json
import os

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/parse-resume/"
INPUT_DIR = "input"
OUTPUT_DIR = "output"
TEST_FILE = "test_resume.pdf"

def run_test_client():
    """
    Sends a test resume to the API and saves the JSON response.
    """
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Path to the test PDF
    file_path = os.path.join(INPUT_DIR, TEST_FILE)

    if not os.path.exists(file_path):
        print(f"Error: Test file not found at {file_path}")
        return

    with open(file_path, "rb") as f:
        files = {"file": (TEST_FILE, f, "application/pdf")}
        
        print(f"Sending request to {API_URL} with file {TEST_FILE}...")
        
        try:
            response = requests.post(API_URL, files=files)
            response.raise_for_status()  # Raise an exception for bad status codes

            # Save the successful response
            output_path = os.path.join(OUTPUT_DIR, "parsed_resume.json")
            with open(output_path, "w") as outfile:
                json.dump(response.json(), outfile, indent=4)
            
            print(f"Successfully parsed resume. Output saved to {output_path}")
            print("\n--- Parsed Data ---")
            print(json.dumps(response.json(), indent=2))
            print("-------------------")


        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            # If the response has content, print it for debugging
            if e.response:
                print("--- Server Response ---")
                print(e.response.text)
                print("-----------------------")


if __name__ == "__main__":
    run_test_client()

