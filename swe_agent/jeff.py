def get_repo_structure(repo):
    """
    Recursively fetch the structure of a repository starting from its root.

    Args:
        repo (github.Repository.Repository): The GitHub repository object.

    Returns:
        str: A formatted string representing the repository structure.
    """
    def list_files(directory):
        structure = []
        contents = repo.get_contents(directory)
        for content in contents:
            if content.type == "dir":
                # Add directory and recurse
                structure.append(f"Directory: {content.path}")
                structure.extend(list_files(content.path))
            else:
                # Add file
                structure.append(f"File: {content.path}")
        return structure

    # Generate the repository structure
    structure_list = list_files("")
    # Join the structure into a single formatted string
    formatted_structure = "\n".join(structure_list)
    # Append the final separator
    return f"--- Repository Structure ---\n{formatted_structure}\n---------------------------"


# import os
# import json
# def get_repo_structure_as_json(cloned_repo_path):
#     """
#     Traverses the local cloned repository and returns its structure in a JSON format.

#     Args:
#         cloned_repo_path (str): Path to the locally cloned repository.

#     Returns:
#         dict: Nested dictionary representation of the repository structure.
#     """
#     def build_tree(path):
#         tree = {}
#         for item in os.listdir(path):
#             item_path = os.path.join(path, item)
#             if os.path.isdir(item_path):
#                 tree[item] = build_tree(item_path)  # Recursive for directories
#             else:
#                 tree[item] = "file"  # Mark as a file
#         return tree

#     repo_structure = build_tree(cloned_repo_path)
#     return repo_structure

import os
def get_repo_structure_as_text(cloned_repo_path):
    """
    Traverses the local cloned repository and returns its structure as a readable string,
    excluding directories and files commonly deemed 'useless' or generated.
    
    Args:
        cloned_repo_path (str): Path to the locally cloned repository.
    
    Returns:
        str: Tree-like plain text representation of the repository structure.
    """
    
    # Directories to ignore by exact name
    IGNORED_DIRNAMES = {
        '.git',      # Git internal folder
        '.svn',      # Subversion
        '.hg',       # Mercurial
        '.idea',     # JetBrains IDE
        '.vscode',   # VSCode
        '__pycache__',
        'node_modules',
        'build',
        'dist',
        'out',
        'target',
        'bin',
        'obj',
        'logs',
        'venv',
        '.venv'
    }

    # Filenames to ignore by exact name
    IGNORED_FILENAMES = {
        '.DS_Store',
        'Thumbs.db',
        'desktop.ini'
    }

    def build_tree_text(path, prefix=""):
        lines = []
        # Sort entries for consistent ordering
        entries = sorted(os.listdir(path))

        # Filter out unwanted items
        filtered_entries = []
        for entry in entries:
            # Full path
            entry_path = os.path.join(path, entry)
            
            # Check if this is a directory or a file
            if os.path.isdir(entry_path):
                # If directory name is in ignored set (or starts with '.')
                if entry in IGNORED_DIRNAMES or entry.startswith('.'):
                    continue
            else:
                # It's a file; check ignored filenames or if it starts with '.'
                if entry in IGNORED_FILENAMES or entry.startswith('.'):
                    continue

            filtered_entries.append(entry)

        for index, entry in enumerate(filtered_entries):
            entry_path = os.path.join(path, entry)
            connector = "└── " if index == len(filtered_entries) - 1 else "├── "

            if os.path.isdir(entry_path):
                lines.append(f"{prefix}{connector}{entry}/")
                lines.extend(
                    build_tree_text(
                        entry_path,
                        prefix + ("    " if index == len(filtered_entries) - 1 else "│   ")
                    )
                )
            else:
                lines.append(f"{prefix}{connector}{entry}")

        return lines

    tree_structure = build_tree_text(cloned_repo_path)
    return "\n".join(tree_structure)




import os
import fnmatch

def is_ignored_dir(dirname):
    """
    Decide if a directory should be ignored altogether.
    """
    # Common directories to ignore entirely
    ignored_dirs = {
        '.git', '.idea', '.vscode', '__pycache__', 'build', 'dist',
        '.mypy_cache', '.pytest_cache', 'node_modules', '.cache'
    }
    return dirname in ignored_dirs or dirname.startswith('.')

def is_test_dir(dirname):
    """
    Decide if a directory name suggests it's primarily for tests.
    """
    # Common directory name patterns for test directories
    test_dir_keywords = ('test', 'tests', 'utests', 'itests', 'functional_tests')
    dirname_lower = dirname.lower()
    return any(k in dirname_lower for k in test_dir_keywords)

def is_test_file(filename):
    """
    Decide if a filename suggests it's a test or test config file.
    """
    # Common test-related filename patterns
    test_file_patterns = [
        'test_*.py',       # e.g. test_something.py
        '*_test.py',       # e.g. something_test.py
        '*test*.py',       # e.g. test_something_else.py or mytestfile.py
    ]
    # Common config files that might define or control tests
    test_config_files = {
        'pytest.ini',
        'tox.ini',
        'noxfile.py',
        'setup.cfg',
        'pyproject.toml',
        'requirements.txt',
        'setup.py',
        'makefile',        # sometimes "Makefile" is capitalized
        'Makefile',
    }

    # Quick checks
    filename_lower = filename.lower()
    # Direct name match with known test config
    if filename in test_config_files or filename_lower in test_config_files:
        return True
    # Pattern matching for test code
    for pattern in test_file_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False

def gather_test_related_files(repo_path):
    """
    Recursively traverse the repo and return a list of paths that are likely test-related.
    """
    test_paths = []

    for root, dirs, files in os.walk(repo_path):
        # Filter out ignored directories in-place (os.walk will skip them)
        dirs[:] = [d for d in dirs if not is_ignored_dir(d)]

        # If the current directory name indicates it's a test directory,
        # we can choose to include *all* files in it or refine further.
        # For demonstration, let's just refine further, but you could do:
        # if is_test_dir(os.path.basename(root)):
        #     # Include all files
        #     for f in files:
        #         test_paths.append(os.path.join(root, f))
        #     continue

        # Otherwise, pick only files that match test patterns
        for f in files:
            if is_test_file(f):
                test_paths.append(os.path.join(root, f))

        # Optionally, if the directory itself is named "test" or "tests",
        # you might want to include everything inside it:
        # if is_test_dir(os.path.basename(root)):
        #     for f in files:
        #         test_paths.append(os.path.join(root, f))

    return test_paths



