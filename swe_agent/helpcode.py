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
    return f"--- Repository Structure ---\n{formatted_structure}\n---------------------------\n"

