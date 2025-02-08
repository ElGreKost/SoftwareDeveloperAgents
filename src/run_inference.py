from crewai import Agent, Task, Crew, LLM
from composio_crewai import ComposioToolSet, Action

from llm_config import get_llm
from repo import get_repo_and_issue
from helpcode import split_directory_tree
from helpcode import extract_paths
from helpcode import check_python_file
import os
from pathlib import Path
import sys
import shutil

import difflib
import time


def run_inference(repo_name: str, issue_number: str, base_commit: str, oracle_retrieval_file: str = "") -> list:
    """
    Runs the entire inference pipeline for a given GitHub repository and issue number,
    splitting large file contexts into chunks, and running the patch creation step
    in parallel across chunks. (Now uses direct file opening instead of gather_file_context.)
    """
    

    #Initialize the LLM
    llm = get_llm()

    #Get repository & issue
    issue_title, issue_body, absolute_path_to_repo = get_repo_and_issue(
        repo_name, issue_number,base_commit
    )
    print("Absolute repository path:", absolute_path_to_repo)

    #if we are given a file path it means we use oraclee retrieval so make the final_file_path be that
    if oracle_retrieval_file:
        print("oracle retrieval is being used")
        relative_to_repo_file_path = oracle_retrieval_file
        final_file_path =  os.path.join(absolute_path_to_repo, relative_to_repo_file_path.lstrip("/"))

    #else run the file selector and file_selector_filterer agents to find the most relevant file and put that in final_file_path
    #huge else block dont need to read it assume it finds final_file_path and go at the end
    else:
        print("oracle retrieval is not being used so we kick off agents to find the file")
        #Split directory tree
        chunks = split_directory_tree(absolute_path_to_repo, token_limit=512)

        #Agent to pick relevant files from each directory chunk
        file_selector = Agent(
            role="File Selector",
            goal=(
                "Read a problem then Look at a long list of files in a repository and pick only one file"
            ),
            backstory=(
                "You are very good at guessing what files contain based on their file path and name."
            ),
            verbose=False,
            llm=llm
        )

        file_selector_task = Task(
            description=(
                "Here is the problem:\n{issue_title}\n{issue_body}\n\n"
                "Here is a list of files.\n"
                "{tree}\n"
                "exclude the files that are for testing!"
                "Try and guess what file does what for the problem"
                "which file from the list is the most likely to cause the problem?\n"
                "pick one file from the given"
            ),
            expected_output=(
                "a file path in the format:\n"
                "- Path: /full/path/to/file.ext"
            ),
            agent=file_selector
        )

        crew = Crew(agents=[file_selector], tasks=[file_selector_task], verbose=False)

        aggregated_file_paths = ""
        for chunk in chunks:
            result = crew.kickoff(
                inputs={
                    "issue_title": issue_title,
                    "issue_body": issue_body,
                    "tree": chunk
                }
            )
            aggregated_file_paths += result.raw + "\n"

        #Filter aggregated file paths
        file_selector_filterer = Agent(
            role="File Selector Filterer",
            goal="Pick the file path that needs changes.",
            backstory="You are good at guessing what files do based on their names",
            llm=llm,
            verbose=False
        )

        file_selector_filterer_task = Task(
            description=(
                "Here is the issue:\n{issue_title}\n\n{issue_body}\n\n"
                "here is a list if file paths:\n{paths}\n\n"
                "Guess what the files contain in the context of the issue"
                "Which file is most likely to contain the code that causes the issue?\n"
                "Return your final answer in the format:\n"
                "- Path: /full/path/to/file.ext\n"
                # "Nothing else. Do **not** add, remove, or modify subfolders."
            ),
            expected_output=(
                "One line with the exact path copied verbatim:\n- Path: /full/path/to/file.ext"
            ),
            agent=file_selector_filterer
        )


        file_filter_crew = Crew(
            agents=[file_selector_filterer],
            tasks=[file_selector_filterer_task],
            verbose=False
        )

        file_filter_result = file_filter_crew.kickoff(
            inputs={
                "issue_title": issue_title,
                "issue_body": issue_body,
                "paths": aggregated_file_paths,
            }
        )

        #extract the final file path
        filtered_text_output = file_filter_result.raw
        chosen_paths = extract_paths(filtered_text_output)
        final_file_path = chosen_paths[0] if chosen_paths else None

        if not final_file_path:
            print("agents found No relevant file paths found. so we skip this issue")
            return ""

        # end of the else block

    # create a backup of final_file_path 
    print("Final chosen file path:", final_file_path)
    directory = os.path.dirname(final_file_path)
    filename = os.path.basename(final_file_path)
    print("Directory:", directory)  # This gives the directory string to cd into.
    print("Filename:", filename)    # This gives the filename string to open it.
    backup_file = final_file_path + ".bak"
    shutil.copy2(final_file_path, backup_file)
    # Get the absolute path of the backup file
    final_file_path_backup = os.path.abspath(backup_file)
    print("Backup created at:", final_file_path_backup)

    composio_toolset = ComposioToolSet(api_key="jhelsrsn9a8shezjwi0ssc")
    tools = composio_toolset.get_tools(actions=[
        'FILETOOL_CHANGE_WORKING_DIRECTORY',
        'FILETOOL_OPEN_FILE',
        'FILETOOL_SCROLL',
        'FILETOOL_EDIT_FILE'
    ])

    python_developer = Agent(
        role='Senior Python Developer',
        goal='Analyze and Correct Python code of a file',
        backstory=(
            "You're an expert Python developer"
        ),
        tools=tools,  # Add Composio tools
        verbose=True,
        llm = llm
    )

    python_developer_task = Task(
        description=(
            "You are tasked with the solving the issue:\n{issue_title}\n{issue_body}\n\n"
            #"use FILETOOL_CHANGE_OPEN_FILE with tool inputs file_path = {file_name} to see the first 100 lines of a file"
            "The file you need to work on is already open"
            "use FILETOOL_SCROLL with tool inputs (direction,lines) direction = down or up , lines  to scroll down or up on the file you opened"
            "use FILETOOL_EDIT_FILE with tool inputs (start_line,text,end_line) the text should be in python programming language"
            "NEVER secify a file_manager_id input"
            "NEVER use FILETOOL_OPEN_FILE"
            "NEVER use FILETOOL_CHANGE_WORKING_DIRECTORY"
        ),
        expected_output="the usage of FILETOOL_SCROLL (direction,lines) or FILETOOL_EDIT_FILE (start_line,text,end_line) the text should be in python programming language",
        agent=python_developer
    )

    python_developer_crew = Crew(
        agents=[python_developer],
        tasks=[python_developer_task],
        verbose=True
    )

    composio_toolset.execute_action(
        action=Action.FILETOOL_CHANGE_WORKING_DIRECTORY,
        params={"path": directory}
    )
    composio_toolset.execute_action(
        action=Action.FILETOOL_OPEN_FILE,
        params={"file_path": filename}
    )

    python_developer_crew.kickoff(
        inputs={
            "issue_title": issue_title,
            "issue_body": issue_body,
            "file_name": filename
        }
    )


    python_compilation_error_solver = Agent(
        role='Senior Python Error Solver',
        goal='Analyze and Correct Python code of a file',
        backstory=(
            "You're an expert Python Error Solver"
        ),
        tools=tools,  # Add Composio tools
        verbose=True,
        llm = llm
    )

    python_compilation_error_task = Task(
        description=(
            "We have a file written in the python programming language that doesnt compiles\n"
            "We get the following error message:\n{error_message}\n"
            #"use FILETOOL_CHANGE_OPEN_FILE with tool inputs file_path = {filename} to see the first 100 lines of a file"
            "The file you need to work on is already open"
            "use FILETOOL_OPEN_FILE ONLY ONCE with tool inputs (file_path = {filename}, line_number=line_of_error - some_lines_for_context)  to see the code that caused the error"
            #"use FILETOOL_CHANGE_SCROLL with tool inputs (direction,lines) direction = down or up , lines  to scroll down or up on the file you opened"
            "use FILETOOL_EDIT_FILE with tool inputs (start_line,text,end_line) the text should be in python programming language"
            "NEVER secify a file_manager_id input"
            #"ONLY USE FILETOOL_OPEN_FILE in {filename}"
            "NEVER use FILETOOL_CHANGE_WORKING_DIRECTORY"
        ),
        #expected_output="the usage of FILETOOL_OPEN_FILE (file_path = {filename}, line_number=line_of_error - some_lines_for_context) or FILETOOL_CHANGE_SCROLL (direction,lines) or FILETOOL_CHANGE_EDIT_FILE (start_line,text,end_line)",
        expected_output="only a single usage of FILETOOL_OPEN_FILE (file_path = {filename}, line_number=line_of_error - some_lines_for_context) then FILETOOL_EDIT_FILE (start_line,text,end_line) to fix the error in python code",
        agent=python_compilation_error_solver
    )

    python_compilation_error_crew = Crew(
        agents=[python_compilation_error_solver],
        tasks=[python_compilation_error_task],
        verbose=True
    )

    maximum_number_of_iterations_to_make_it_compile = 5
    iterations = 0

    while iterations < maximum_number_of_iterations_to_make_it_compile:
        success, message = check_python_file(final_file_path)
        print("\n\n\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print(message)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n\n")
        time.sleep(60)
        if success:
            print("The file compiles successfully.")
            break
        else:
            # composio_toolset.execute_action(
            #     action=Action.FILETOOL_OPEN_FILE,
            #     params={"file_path": filename}
            # )
            python_compilation_error_crew.kickoff(
                inputs={
                    "filename": filename,
                    "error_message": message
                }      
            )
        iterations += 1

    if iterations == maximum_number_of_iterations_to_make_it_compile:
        print("Reached maximum number of iterations. The file may still have compilation errors.")

    # Get the final diff
    relative_path = os.path.relpath(final_file_path, absolute_path_to_repo) 
    print("relative path:", relative_path)
    with open(final_file_path_backup, "r") as f:
        backup_lines = f.readlines()
    with open(final_file_path, "r") as f:
        final_lines = f.readlines()

    # Generate the unified diff patch
    diff_patch = difflib.unified_diff(
        backup_lines,
        final_lines,
        fromfile="a/" + relative_path,
        tofile="b/" + relative_path,
        # lineterm defaults to "\n" if omitted
    )
    patch_lines = list(diff_patch)
    diff_header = f"diff --git a/{relative_path} b/{relative_path}"
    if patch_lines:
        patch_lines.insert(0, diff_header)
    # Since each line already ends with a newline, simply join them with an empty separator:
    patch_str = "".join(patch_lines)
 
    # Clean up the cloned repo
    try:
        shutil.rmtree(Path(absolute_path_to_repo))
        print(f"Deleted repository directory: {absolute_path_to_repo}")
    except Exception as e:
        print(f"Error deleting repository directory: {e}")

    return patch_str


