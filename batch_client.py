import asyncio
import aiohttp
import os
import json

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/parse-resume/"
INPUT_DIR = "input"
OUTPUT_DIR = "output"

async def process_file(session: aiohttp.ClientSession, file_path: str):
    """
    Sends a single PDF file to the API and saves the response.
    """
    file_name = os.path.basename(file_path)
    output_filename = os.path.splitext(file_name)[0] + ".json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    try:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_name, content_type='application/pdf')

            print(f"-> Sending {file_name}...")
            async with session.post(API_URL, data=data) as response:
                response.raise_for_status()
                result = await response.json()

                with open(output_path, "w") as outfile:
                    json.dump(result, outfile, indent=4)
                
                print(f"<- Success: {file_name} -> {output_filename}")
                return (file_name, "Success")

    except aiohttp.ClientError as e:
        print(f"<- Error processing {file_name}: {e}")
        return (file_name, f"Error: {e}")
    except Exception as e:
        print(f"<- An unexpected error occurred with {file_name}: {e}")
        return (file_name, f"Unexpected Error: {e}")

async def main():
    """
    Finds all PDFs in the input directory and processes them concurrently.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    pdf_files = [os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"No PDF files found in the '{INPUT_DIR}' directory.")
        return

    print(f"Found {len(pdf_files)} PDF files to process.")

    async with aiohttp.ClientSession() as session:
        tasks = [process_file(session, file_path) for file_path in pdf_files]
        results = await asyncio.gather(*tasks)

    print("\n--- Batch Processing Summary ---")
    for filename, status in results:
        print(f"{filename}: {status}")
    print("--------------------------------")


if __name__ == "__main__":
    asyncio.run(main())