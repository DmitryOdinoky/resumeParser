#!/usr/bin/env python3
"""
Comprehensive test script for the Resume Parser API
Tests various functionalities including:
- Single file parsing
- Batch processing
- OCR capabilities
- Error handling
- PDF text extraction
"""

import os
import sys
import json
import requests
import argparse
from typing import Dict, List, Optional
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

# Configuration
API_URL = "http://127.0.0.1:8000/parse-resume/"
INPUT_DIR = "input"
OUTPUT_DIR = "output"

class Colors:
    """ANSI color codes for terminal output"""
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    WARNING = Fore.YELLOW
    INFO = Fore.CYAN
    RESET = Style.RESET_ALL


def print_colored(message: str, color: str = Colors.INFO):
    """Print colored message to terminal"""
    print(f"{color}{message}{Colors.RESET}")


def print_section_header(title: str):
    """Print a formatted section header"""
    print(f"\n{Colors.INFO}{'='*80}")
    print(f"{title.center(80)}")
    print(f"{'='*80}{Colors.RESET}\n")


def test_pdf_extraction(file_path: str) -> tuple[str, bool]:
    """
    Test PDF text extraction with and without OCR
    Returns: (extracted_text, used_ocr)
    """
    try:
        # First try regular text extraction
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        if len(text.strip()) > 0:
            return text, False
        
        # If no text, try OCR
        print_colored(f"No text extracted with PyMuPDF, trying OCR...", Colors.WARNING)
        images = convert_from_path(file_path, dpi=300)
        
        for i, image in enumerate(images):
            page_text = pytesseract.image_to_string(image)
            if page_text:
                text += page_text + "\n"
            print_colored(f"  OCR Page {i+1}: Extracted {len(page_text)} characters", Colors.INFO)
        
        return text, True
        
    except Exception as e:
        print_colored(f"Error extracting text: {e}", Colors.ERROR)
        return "", False


def test_single_file(file_path: str, save_output: bool = True) -> Optional[Dict]:
    """Test parsing a single PDF file"""
    if not os.path.exists(file_path):
        print_colored(f"Error: File not found at {file_path}", Colors.ERROR)
        return None
    
    file_name = os.path.basename(file_path)
    print_colored(f"Testing: {file_name}", Colors.INFO)
    
    # Test text extraction first
    print_colored("  1. Testing text extraction...", Colors.INFO)
    text, used_ocr = test_pdf_extraction(file_path)
    
    if len(text.strip()) == 0:
        print_colored("     ❌ No text could be extracted", Colors.ERROR)
    else:
        ocr_msg = " (using OCR)" if used_ocr else ""
        print_colored(f"     ✓ Extracted {len(text)} characters{ocr_msg}", Colors.SUCCESS)
        print_colored(f"     First 200 chars: {text[:200].replace(chr(10), ' ')}...", Colors.INFO)
    
    # Test API parsing
    print_colored("  2. Testing API parsing...", Colors.INFO)
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_name, f, "application/pdf")}
            response = requests.post(API_URL, files=files)
        
        if response.status_code == 200:
            data = response.json()
            print_colored("     ✓ Successfully parsed", Colors.SUCCESS)
            print_colored(f"     Name: {data.get('full_name', 'N/A')}", Colors.INFO)
            print_colored(f"     Email: {data.get('email', 'N/A')}", Colors.INFO)
            print_colored(f"     Phone: {data.get('phone', 'N/A')}", Colors.INFO)
            print_colored(f"     Industries: {', '.join(data.get('industry', []))}", Colors.INFO)
            
            # Save output if requested
            if save_output:
                output_path = os.path.join(OUTPUT_DIR, file_name.replace('.pdf', '.json'))
                with open(output_path, 'w') as out_file:
                    json.dump(data, out_file, indent=4)
                print_colored(f"     ✓ Saved to: {output_path}", Colors.SUCCESS)
            
            return data
        else:
            print_colored(f"     ❌ Error {response.status_code}: {response.text}", Colors.ERROR)
            return None
            
    except Exception as e:
        print_colored(f"     ❌ Request failed: {e}", Colors.ERROR)
        return None


def test_batch_processing(directory: str = INPUT_DIR) -> Dict[str, bool]:
    """Test batch processing of all PDFs in a directory"""
    results = {}
    
    pdf_files = [f for f in os.listdir(directory) if f.endswith('.pdf')]
    
    if not pdf_files:
        print_colored(f"No PDF files found in {directory}", Colors.WARNING)
        return results
    
    print_colored(f"Found {len(pdf_files)} PDF files to process", Colors.INFO)
    
    for pdf_file in pdf_files:
        file_path = os.path.join(directory, pdf_file)
        result = test_single_file(file_path, save_output=True)
        results[pdf_file] = result is not None
        print()  # Add spacing between files
    
    return results


def test_server_health():
    """Test if the API server is running"""
    try:
        # Try a simple GET request to the root
        response = requests.get("http://127.0.0.1:8000/")
        return True
    except requests.exceptions.ConnectionError:
        return False


def print_summary(results: Dict[str, bool]):
    """Print test summary"""
    total = len(results)
    successful = sum(1 for v in results.values() if v)
    failed = total - successful
    
    print_section_header("TEST SUMMARY")
    
    print_colored(f"Total files tested: {total}", Colors.INFO)
    print_colored(f"Successful: {successful}", Colors.SUCCESS)
    print_colored(f"Failed: {failed}", Colors.ERROR if failed > 0 else Colors.SUCCESS)
    
    if failed > 0:
        print_colored("\nFailed files:", Colors.ERROR)
        for file_name, success in results.items():
            if not success:
                print_colored(f"  - {file_name}", Colors.ERROR)
    
    print_colored(f"\nSuccess rate: {(successful/total*100):.1f}%", 
                 Colors.SUCCESS if successful/total >= 0.8 else Colors.WARNING)


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test Resume Parser API")
    parser.add_argument('--file', '-f', help='Test a single file')
    parser.add_argument('--batch', '-b', action='store_true', help='Run batch processing')
    parser.add_argument('--all', '-a', action='store_true', help='Run all tests')
    parser.add_argument('--no-save', action='store_true', help='Don\'t save output files')
    args = parser.parse_args()
    
    print_section_header("RESUME PARSER TEST SUITE")
    
    # Check server health
    print_colored("Checking API server...", Colors.INFO)
    if not test_server_health():
        print_colored("❌ API server is not running!", Colors.ERROR)
        print_colored("Please start the server with: uvicorn main:app --reload", Colors.WARNING)
        sys.exit(1)
    else:
        print_colored("✓ API server is running", Colors.SUCCESS)
    
    results = {}
    
    # Run tests based on arguments
    if args.file:
        print_section_header("SINGLE FILE TEST")
        result = test_single_file(args.file, save_output=not args.no_save)
        results[os.path.basename(args.file)] = result is not None
        
    elif args.batch or args.all:
        print_section_header("BATCH PROCESSING TEST")
        results = test_batch_processing()
        
    else:
        # If no arguments, run a comprehensive test
        print_section_header("COMPREHENSIVE TEST")
        
        # Test specific files that are known to have different characteristics
        test_files = [
            ("input/Dmitry Odinoky CV.pdf", "Scanned/Image PDF (requires OCR)"),
            ("input/Dmitry Odinoky_CV_Back-End_Machine Learning Engineer.pdf", "Regular text PDF"),
            ("input/Milan K O.pdf", "Simple format PDF"),
        ]
        
        for file_path, description in test_files:
            if os.path.exists(file_path):
                print_colored(f"\nTesting {description}:", Colors.WARNING)
                result = test_single_file(file_path, save_output=not args.no_save)
                results[os.path.basename(file_path)] = result is not None
            else:
                print_colored(f"Skipping {file_path} (not found)", Colors.WARNING)
        
        # Then run batch on remaining files
        if len(results) < len([f for f in os.listdir(INPUT_DIR) if f.endswith('.pdf')]):
            print_section_header("TESTING REMAINING FILES")
            batch_results = test_batch_processing()
            results.update(batch_results)
    
    # Print summary
    if results:
        print_summary(results)


if __name__ == "__main__":
    main()