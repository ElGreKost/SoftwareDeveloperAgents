import os
import subprocess
import sys
import venv
from pathlib import Path

def create_virtualenv(venv_path: Path):
    """
    Create a virtual environment at the specified path.

    Parameters:
    - venv_path (Path): The path where the virtual environment will be created.
    """
    try:
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(venv_path)
        print(f"Created virtual environment at {venv_path}")
    except Exception as e:
        print(f"Error creating virtual environment: {e}")
        sys.exit(1)

def install_dependencies(venv_path: Path, project_dir: Path):
    """
    Install dependencies from pyproject.toml into the virtual environment.

    Parameters:
    - venv_path (Path): The path to the virtual environment.
    - project_dir (Path): The directory of the cloned project containing pyproject.toml.
    """
    # Determine the path to the venv's Python executable (Linux)
    python_executable = venv_path / 'bin' / 'python'

    # Upgrade pip to ensure the latest features are available
    try:
        subprocess.check_call([str(python_executable), '-m', 'pip', 'install', '--upgrade', 'pip'], cwd=project_dir)
        print("Upgraded pip in the virtual environment.")
    except subprocess.CalledProcessError as e:
        print(f"Error upgrading pip: {e}")
        sys.exit(1)

    # Install dependencies using pip
    try:
        # Check if pyproject.toml specifies a build system (like poetry or setuptools)
        # For simplicity, we'll assume pip can install the project directly
        subprocess.check_call([str(python_executable), '-m', 'pip', 'install', '.'], cwd=project_dir)
        print("Installed dependencies from pyproject.toml into the virtual environment.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

