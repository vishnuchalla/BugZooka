import re
import subprocess
from src.prompts import ERROR_SUMMARIZATION_PROMPT


def download_prow_logs(url, output_dir="/tmp/"):
    """
    Extracts the GCS path from the URL and downloads the entire log directory.
    
    :param prow_url: The Prow CI log URL
    :param output_dir: Directory where logs should be stored (default: current directory)
    :return: BuildID for futher processing
    """
    # Extract build ID from the URL (last part after the last '/')
    match = re.search(r"/(\d+)$", url)
    if not match:
        raise ValueError("Invalid URL format: Cannot extract build ID")
    
    build_id = match.group(1)
    
    # Extract the GCS path from the URL
    if "view/gs/" in url:
        gcs_path = url.split("view/gs/")[1]
    else:
        raise ValueError("Invalid Prow URL: GCS path not found.")

    # Construct the gsutil command
    gsutil_command = f"gsutil -m cp -r gs://{gcs_path}/ {output_dir}"

    # Execute the command
    try:
        print(f"Executing: {gsutil_command}")
        subprocess.run(gsutil_command, shell=True, check=True)
        print("Logs downloaded successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading logs: {e}")
    return output_dir + build_id

def search_errors_in_file(file_path):
    """
    Opens a log file and searches for error terms.
    
    Args:
        file_path (str): The path of the log file to search for errors.
        
    Returns:
        List: A list of lines containing error terms.
    """
    error_keywords = ["error", "failure", "exception", "fatal", "panic", "traceback"]
    error_lines = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if any(keyword in line.lower() for keyword in error_keywords):
                    error_lines.append(line.strip())  # Add the line if it contains error keywords
        
        if error_lines:
            print(f"Found {len(error_lines)} error lines in {file_path}:")
            return error_lines
        else:
            print(f"No errors found in {file_path}.")
            return []

    except Exception as e:
        print(f"Error opening the file {file_path}: {e}")
        return []

def generate_prompt(error_list):
    """Generates a structured prompt for the LLM to analyze relevant error logs."""
    # Convert to messages list format
    messages = [
        {"role": "system", "content": ERROR_SUMMARIZATION_PROMPT["system"]},
        {"role": "user", "content": ERROR_SUMMARIZATION_PROMPT["user"].format(error_list="\n".join(error_list))},
        {"role": "assistant", "content": ERROR_SUMMARIZATION_PROMPT["assistant"]}
    ]
    return messages
