def json_to_list_dict(json_path):
    """
    Reads a JSON dataset and returns it as a list of dictionaries **without modifications**.

    Parameters:
        json_path (str): Path to the JSON file.

    Returns:
        list[dict]: A list of dictionaries exactly as they appear in the JSON file.
    """
    dataset_path = Path(json_path)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file {dataset_path} not found.")

    with open(dataset_path, "r") as f:
        data = json.load(f)

    return data  # Returning the raw data without modifications



import re

def extract_file_paths_from_patches(diff_text):
    """
    Extracts file paths affected from a git diff string.
    
    Parameters:
        diff_text (str): A string containing a diff output.
    
    Returns:
        list[str]: A list of file paths (without the 'a/' or 'b/' prefixes).
    """
    # The regex matches lines starting with "diff --git" followed by two paths.
    # We capture the file path from the "a/" part.
    pattern = re.compile(r"^diff --git a/(.+?) b/", re.MULTILINE)
    
    # Find all matches
    paths = pattern.findall(diff_text)
    
    # Remove duplicates (if any) and return
    return list(dict.fromkeys(paths))


import re
def extract_paths(text: str) -> list:
    """Extract file paths from text using regex."""
    pattern = r'(?:- Path: |Path: |File: )(/\S+.*)'
    return re.findall(pattern, text)



def approximate_token_count_by_chars(text: str, chars_per_token: float = 4.0) -> int:
    """
    Approximates the token count by assuming an average token length.
    Default is 4 characters per token, which is a rough heuristic.
    """
    return int(len(text) / chars_per_token)

import os
def gather_directory_descriptions(root_path: str, base_path: str = None) -> list[str]:
    """
    Walks the root_path directory, collecting lines describing all .py files.
    If base_path is given, each path is made relative to base_path; 
    otherwise, absolute paths are used.
    
    Returns:
        List[str]: A list of lines, each in the format "- Path: /some/path.py"
    """
    description_lines = []
    for root, dirs, files in os.walk(root_path):
        for f in files:
            if f.endswith(".py"):
                abs_path = os.path.join(root, f)
                if base_path:
                    # Convert to relative path
                    rel_path = os.path.relpath(abs_path, start=base_path)
                    line = f"- Path: {rel_path}"
                else:
                    # Use absolute path
                    line = f"- Path: {abs_path}"
                description_lines.append(line)
    return description_lines
def split_directory_tree(
    root_path: str, 
    token_limit: int = 10000, 
    avg_chars_per_token: float = 4.0, 
    base_path: str = None
) -> list[str]:
    """
    1. Gathers one-string-per-Python-file using `gather_directory_descriptions`. 
       If base_path is provided, .py paths are made relative to base_path; 
       otherwise, absolute paths are used.
    2. Merges these path strings into chunks so that each chunk is under
       `token_limit` tokens (approx) based on `approximate_token_count_by_chars`.

    Args:
      root_path (str): The root directory to walk for .py files.
      token_limit (int): Approximate max tokens per chunk.
      avg_chars_per_token (float): Conversion factor from characters to tokens.
      base_path (str, optional): If provided, paths are made relative to this folder.

    Returns:
      list[str]: A list of string chunks that can be fed to an LLM.
                 Each chunk is a concatenation of lines, each line looking like
                 "- Path: /abs/or/relative/path.py"
    """
    # Step 1: Gather .py file descriptions
    directory_descriptions = gather_directory_descriptions(root_path, base_path=base_path)

    # Step 2: Split them into chunks based on token_limit
    subtrees = []
    current_chunk_lines = []
    current_token_count = 0

    for desc in directory_descriptions:
        # Estimate the token usage for this line
        desc_tokens = approximate_token_count_by_chars(desc, avg_chars_per_token)
        # If adding this line would exceed token_limit, start a new chunk
        if current_token_count + desc_tokens > token_limit and current_chunk_lines:
            subtrees.append("\n".join(current_chunk_lines))
            current_chunk_lines = []
            current_token_count = 0

        current_chunk_lines.append(desc)
        current_token_count += desc_tokens

    # Append the final chunk if any lines remain
    if current_chunk_lines:
        subtrees.append("\n".join(current_chunk_lines))

    return subtrees





import json
from pathlib import Path

def append_dict_to_jsonl(data: dict, jsonl_file: Path) -> None:
    """
    Appends a dictionary to a JSONL file.
    
    Each dictionary is written as a JSON object on a new line.
    
    Parameters:
        data (dict): The dictionary to append.
        jsonl_file (Path): The path to the JSONL file.
    """
    # Open the file in append mode and write the JSON object followed by a newline.
    with jsonl_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")



    




def extract_relative_path_from_patch(patch_text):
    # This will find the first diff header and capture the relative path after "a/"
    match = re.search(r"^diff --git a/(\S+)\s+b/\S+", patch_text, re.MULTILINE)
    if match:
        return match.group(1)
    return None


def check_python_file(file_path):
    """
    Check if the Python file at file_path compiles.

    Returns:
        (bool, str): A tuple where the first element is True if the file
                     compiles without syntax errors, and False otherwise.
                     The second element is a message: either a success
                     message or details about the syntax error.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            source = file.read()
        # Try to compile the source code.
        compile(source, file_path, 'exec')
        return True, "Compilation successful!"
    except SyntaxError as e:
        # Format the error message with as much detail as possible.
        error_message = (
            f"Syntax error in file {e.filename} at line {e.lineno}, offset {e.offset}:\n"
        )
        if e.text:
            error_message += f"  {e.text.strip()}\n"
        error_message += f"{e.msg}"
        return False, error_message
    except Exception as e:
        # Catch other exceptions (such as encoding errors)
        return False, f"Error: {e}"