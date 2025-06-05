import re
import subprocess
import requests
from collections import deque
from src.prompts import ERROR_SUMMARIZATION_PROMPT


def download_url_to_log(url, log_file_path):
    """
    Downloads the content from a given URL and writes it to a log file.

    Args:
        url (str): The URL to download content from.
        log_file_path (str): The path to the log file.
    """
    output_dir = "/tmp"
    log_file_path = output_dir + log_file_path
 
    print(f"Creating a file {log_file_path}")
    try:
        response = requests.get(url, stream=True, verify=False)
        response.raise_for_status()
        
        with open(log_file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Successfully downloaded content from {url} to {log_file_path}")
    
    except requests.exceptions.RequestException as e:
         print(f"Error downloading from {url}: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return output_dir

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

def search_errors_in_file(file_path, context_lines=3):
    """
    Opens a log file and searches for error terms while capturing context.
    
    Args:
        file_path (str): The path of the log file to search for errors.
        context_lines (int): Number of lines to include before and after the error.
        
    Returns:
        List: A list of error contexts, each containing surrounding lines.
    """
    error_keywords = ["error", "failure", "exception", "fatal", "panic"]
    error_contexts = []
    previous_lines = deque(maxlen=context_lines)

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            log_lines = f.readlines()
        
        for i, line in enumerate(log_lines):
            if any(keyword in line.lower() for keyword in error_keywords):
                # Capture context lines before and after the error
                start = max(0, i - context_lines)
                end = min(len(log_lines), i + context_lines + 1)
                error_snippet = log_lines[start:end]
                error_contexts.append("".join(error_snippet).strip())

            previous_lines.append(line)

        if error_contexts:
            print(f"Found {len(error_contexts)} errors with context in {file_path}:")
            return error_contexts
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
