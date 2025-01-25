import os
import re

IGNORED_DIRS = {
    '.git', '.idea', '.vscode', '__pycache__',
    'build', 'dist', '.mypy_cache', '.pytest_cache', 'node_modules'
}

VERSIONING_FILES = {
    # "Versioning" or "dependency" files we want to appear in the tree:
    '.bumpversion.cfg', 'versioneer.py', 'setup.py', 'setup.cfg',
    'pyproject.toml', 'requirements.txt', 'Pipfile', 'Pipfile.lock',
    'tox.ini', 'environment.yml', 'constraints.txt', 'Makefile',
    '.pre-commit-config.yaml',
}

# Patterns to identify lines we care about for each file type:
# Adjust or expand these patterns to fit your environment.
TARGET_LINE_PATTERNS = {
    'pyproject.toml': [
        r'\[project\.optional-dependencies\]', 
        r'\[tool\.pytest\.ini_options\]', 
        r'doc', 
        r'test'
    ],
    'setup.cfg': [
        r'\[options\.extras_require\]', 
        r'test\s*=', 
        r'\[options\.entry_points\]'
    ],
    'setup.py': [
        # If you want any line referencing 'test' or 'doc' in setup.py
        r'test', 
        r'doc'
    ],
    'Makefile': [
        r'pytest\s+--doctest-rst', 
        r'make\s+test'
    ],
    'conftest.py': [
        r'import\s+hypothesis', 
        r'import\s+pytest_astropy'
    ],
}

def build_versioning_tree_and_snippets(repo_path):
    """
    1) Recursively scan the repo, ignoring certain directories.
    2) Identify 'versioning' files (by name or extension).
    3) Build a tree-like structure of only those directories containing these files.
    4) For specific files (pyproject.toml, setup.cfg, docs/Makefile, conftest.py, etc.),
       extract only relevant lines based on known patterns.
    5) Return both the tree and a string of snippet lines.
    """

    relevant_paths = set()

    # 1) Collect all relevant file paths by name
    for root, dirs, files in os.walk(repo_path, topdown=True):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]

        for f in files:
            f_lower = f.lower()
            full_path = os.path.join(root, f)
            # Check if it's a known versioning file or has relevant extension
            if f_lower in VERSIONING_FILES or any(f_lower.endswith(ext) for ext in ['.ini', '.cfg', '.toml']):
                relevant_paths.add(full_path)

    # 2) Helper: check if a directory or its children contains relevant files
    def contains_relevant_items(dir_path):
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path) and item_path in relevant_paths:
                    return True
                if os.path.isdir(item_path):
                    if contains_relevant_items(item_path):
                        return True
        except PermissionError:
            pass
        return False

    # 3) Build the tree (directories + relevant files)
    def build_tree_text(current_path, prefix=""):
        lines = []
        try:
            entries = sorted(
                [e for e in os.listdir(current_path)
                 if not e.startswith('.') and e not in IGNORED_DIRS],
                key=str.lower
            )
        except PermissionError:
            return lines

        for i, entry in enumerate(entries):
            entry_path = os.path.join(current_path, entry)
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "

            if os.path.isdir(entry_path):
                if contains_relevant_items(entry_path):
                    lines.append(f"{prefix}{connector}{entry}/")
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    lines.extend(build_tree_text(entry_path, new_prefix))
            else:
                if entry_path in relevant_paths:
                    lines.append(f"{prefix}{connector}{entry}")
        return lines

    tree_lines = [os.path.basename(repo_path) + "/"]
    tree_lines += build_tree_text(repo_path, prefix="")
    tree_string = "\n".join(tree_lines)

    # 4) Gather only relevant lines (snippets) from certain files
    #    If the file isn't in our 'TARGET_LINE_PATTERNS' of interest,
    #    we won't show any snippet lines (unless you want otherwise).
    snippet_sections = []
    for path in sorted(relevant_paths):
        relative_path = os.path.relpath(path, repo_path)

        # Decide if we should parse lines from this file
        filename = os.path.basename(path)
        # We'll match ignoring case, so let's keep it in lowercase form for patterns
        filename_lower = filename.lower()

        # We look up patterns by "file type" or extension
        patterns = []
        if filename_lower in TARGET_LINE_PATTERNS:
            # e.g. "pyproject.toml", "setup.cfg", "makefile", "conftest.py"
            patterns = TARGET_LINE_PATTERNS[filename_lower]
        elif filename_lower.endswith('.toml'):
            # might be "pyproject.toml" or some other .toml
            # if not specifically "pyproject.toml", we skip or define general rules
            if 'pyproject.toml' in TARGET_LINE_PATTERNS:
                patterns = TARGET_LINE_PATTERNS['pyproject.toml']
        elif filename_lower.endswith('.cfg'):
            # might be "setup.cfg" or another .cfg
            if 'setup.cfg' in TARGET_LINE_PATTERNS:
                patterns = TARGET_LINE_PATTERNS['setup.cfg']
        elif filename_lower == 'makefile':
            # docs/Makefile
            if 'makefile' in TARGET_LINE_PATTERNS:
                patterns = TARGET_LINE_PATTERNS['makefile']
        elif filename_lower == 'conftest.py':
            # conftest
            if 'conftest.py' in TARGET_LINE_PATTERNS:
                patterns = TARGET_LINE_PATTERNS['conftest.py']
        elif filename_lower == 'setup.py':
            if 'setup.py' in TARGET_LINE_PATTERNS:
                patterns = TARGET_LINE_PATTERNS['setup.py']

        # if no patterns matched, we skip collecting lines from this file
        if not patterns:
            continue

        # We'll gather only lines that match at least one pattern
        matched_lines = []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    for pat in patterns:
                        if re.search(pat, line, re.IGNORECASE):
                            matched_lines.append(line.rstrip("\n"))
                            break  # No need to check other patterns if one matched
        except Exception as e:
            matched_lines.append(f"Error reading file: {e}")

        if matched_lines:
            snippet_text = "\n".join(matched_lines)
            snippet_sections.append(f"===== {relative_path} =====\n{snippet_text}\n")

    snippets_string = "\n".join(snippet_sections)

    return tree_string, snippets_string