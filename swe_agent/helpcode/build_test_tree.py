import os
import fnmatch

##############################################################################
# 1. Identify test-related paths
##############################################################################

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
        '*test*.py',       # e.g. mytestfile.py or test_something_else.py
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
        'makefile',  # sometimes "Makefile" is capitalized
        'Makefile',
    }

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
    Recursively traverse the repo and return a list of *relative* paths
    that are likely test-related.
    """
    test_paths = []

    # Record the absolute repo path length for easy slicing later
    repo_path = os.path.abspath(repo_path)
    base_len = len(repo_path.rstrip(os.sep)) + 1

    for root, dirs, files in os.walk(repo_path):
        # Filter out ignored directories in-place (os.walk will skip them)
        dirs[:] = [d for d in dirs if not is_ignored_dir(d)]

        # Option A: if the directory name is a known "test" directory,
        # you could include *everything* in it. For demonstration, we won't do that
        # automatically. We’ll still check is_test_file() for each file.
        # 
        # If you want to include everything from a 'tests' dir, uncomment the lines below:
        #
        # if is_test_dir(os.path.basename(root)):
        #     for f in files:
        #         relative_path = os.path.join(root, f)[base_len:]
        #         test_paths.append(relative_path)
        #     continue

        for f in files:
            if is_test_file(f):
                full_path = os.path.join(root, f)
                # Convert to a path relative to the repo's root
                relative_path = full_path[base_len:]
                test_paths.append(relative_path)

    return test_paths

##############################################################################
# 2. Build a minimal tree from the gathered file paths
##############################################################################

def build_nested_dict_from_paths(paths):
    """
    Given a list of relative file paths, build a nested dictionary structure:
    {
      'tests': {
        'unit': {
          'test_something.py': None,
          'test_another.py': None
        },
        'integration': {
          'test_integration.py': None
        }
      },
      'pytest.ini': None
    }

    Keys = directories/files; 'None' indicates a file leaf.
    """
    root_dict = {}

    for path in paths:
        parts = path.split(os.sep)
        current_dict = root_dict

        for i, part in enumerate(parts):
            # If we're at the last part, it's a file
            if i == len(parts) - 1:
                current_dict.setdefault(part, None)
            else:
                # It's a directory level
                if part not in current_dict:
                    current_dict[part] = {}
                current_dict = current_dict[part]

    return root_dict

def build_tree_string(nested_dict, prefix=""):
    """
    Recursively build a string representation of the nested directory structure.
    """
    # Sort keys for consistent ordering
    items = sorted(nested_dict.keys())
    lines = []
    for i, key in enumerate(items):
        connector = "└── " if i == len(items) - 1 else "├── "
        # If this is a directory (value is a dict)
        if isinstance(nested_dict[key], dict):
            lines.append(f"{prefix}{connector}{key}/")
            # Recurse into sub-dict
            sub_prefix = prefix + ("    " if i == len(items) - 1 else "│   ")
            lines.append(build_tree_string(nested_dict[key], prefix=sub_prefix))
        else:
            # It's a file (None)
            lines.append(f"{prefix}{connector}{key}")
    return "\n".join(lines)

##############################################################################
# Main logic: gather test files, build tree, get string
##############################################################################

def build_test_tree(repo_path):
    """
    1. Gather test-related files
    2. Convert them into a nested dict structure
    3. Return a single string in a tree-like format
    """
    test_files = gather_test_related_files(repo_path)
    nested_dict = build_nested_dict_from_paths(test_files)
    if not nested_dict:
        return "No test-related files found."
    return build_tree_string(nested_dict)