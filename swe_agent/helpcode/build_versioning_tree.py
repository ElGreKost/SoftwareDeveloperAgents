import os

# -----------------------------------
# 1) Configure which items to ignore
# -----------------------------------
IGNORED_DIRS = {
    '.git', '.idea', '.vscode', '__pycache__',
    'build', 'dist', '.mypy_cache', '.pytest_cache', 'node_modules'
}

# -----------------------------------
# 2) Configure versioning/dependency filenames
#    (We're calling these "versioning" broadly, to include
#    files often involved in build/version management.)
# -----------------------------------
VERSIONING_FILES = {
    '.bumpversion.cfg',
    'versioneer.py',
    'setup.py',
    'setup.cfg',
    'pyproject.toml',
    'requirements.txt',
    'pipfile',
    'environment.yml',
    'constraints.txt',
    'makefile',    # some projects use Makefile for install/version tasks
    'Makefile',
}

def build_versioning_tree(repo_path):
    """
    Recursively build a tree structure of directories and files that:
      - Are recognized as "versioning" files (by name).

    Returns a multi-line string that visually represents this tree.
    """

    # 1) Identify all "relevant" file paths
    relevant_paths = set()

    for root, dirs, files in os.walk(repo_path, topdown=True):
        # Filter out ignored directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]

        for f in files:
            f_lower = f.lower()
            full_path = os.path.join(root, f)
            # Check if the file name (case-insensitive) is in VERSIONING_FILES
            if f_lower in VERSIONING_FILES:
                relevant_paths.add(full_path)

    # 2) Function to check if a directory (or any of its subdirectories) contains relevant files
    def contains_relevant_items(dir_path):
        # Check current directory's files
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                # If it's a file that's relevant, return True
                if os.path.isfile(item_path) and item_path in relevant_paths:
                    return True

            # Otherwise, check subdirectories
            for d in os.listdir(dir_path):
                sub_path = os.path.join(dir_path, d)
                if os.path.isdir(sub_path) and not d.startswith('.') and d not in IGNORED_DIRS:
                    if contains_relevant_items(sub_path):
                        return True
        except PermissionError:
            # In case we hit a directory we can't read, just skip it
            pass

        return False

    # 3) Recursively build the tree string, but only include directories/files with relevant items
    def build_tree_text(current_path, prefix=""):
        lines = []
        # Collect entries (dirs+files), ignoring hidden/ignored
        try:
            entries = sorted(
                [e for e in os.listdir(current_path)
                 if not e.startswith('.') and e not in IGNORED_DIRS],
                key=str.lower
            )
        except PermissionError:
            return lines  # can't read this directory, skip

        for i, entry in enumerate(entries):
            entry_path = os.path.join(current_path, entry)
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "

            if os.path.isdir(entry_path):
                # Only recurse if this directory (or children) has relevant items
                if contains_relevant_items(entry_path):
                    lines.append(f"{prefix}{connector}{entry}/")
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    lines.extend(build_tree_text(entry_path, new_prefix))
            else:
                # It's a file - include if it's in relevant paths
                if entry_path in relevant_paths:
                    lines.append(f"{prefix}{connector}{entry}")

        return lines

    # 4) Start the tree from the top-level repo directory
    tree_lines = [os.path.basename(repo_path) + "/"]
    tree_lines += build_tree_text(repo_path, prefix="")

    return "\n".join(tree_lines)