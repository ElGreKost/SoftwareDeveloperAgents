from pathlib import Path
from helpcode import json_to_list_dict  # Replace 'your_module' with the actual module name
from helpcode import extract_relative_path_from_patch
from helpcode import append_dict_to_jsonl
from run_inference import run_inference


from pathlib import Path
import sys
from dotenv import load_dotenv

#define the dataset to run inference on. must be a json inside the dataset directory
dataset = "reduced_to_50_swe_bench_dataset.json"

def main():

    #load the environment variables
    load_dotenv(dotenv_path=Path("../.env"))

    dataset_path_relative_to_helpcode = Path("../datasets/"+dataset)
    print("\nUsing dataset: ", dataset_path_relative_to_helpcode.resolve(),"\n")

    output_file = Path("../datasets/patches.jsonl")
    print("THe output file will be saved at: ", output_file.resolve(), "you can run swe bench evaluation on it\n")

    output_file.write_text("")  # clear the output file
    
    #load the dataset you want from the datasets directory and make it a dictionary
    try:
        repo_issue_dataset = json_to_list_dict(dataset_path_relative_to_helpcode)
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return
    

    # if you want a subset of the dataset, you can specify the instance ids you want to run inference on
    allowed_instance_ids = {
        "pallets__flask-4045", 
        "pallets__flask-4992",
        "psf__requests-1963"
    }
    

    #iterate through the dataset and run inference
    for entry in repo_issue_dataset:
        repo_name = entry["repo"]
        instance_id   = entry["instance_id"]
        base_commit = entry["base_commit"]

        if instance_id not in allowed_instance_ids:
            continue  # Skip entries if using subset

        issue_number = instance_id.split("-")[-1]

        # get the oracle retrieval relative file path
        patch = entry["patch"]
        oracle_retrieval_file_path = extract_relative_path_from_patch(patch)
        #oracle_retrieval_file_path = ""


        model_patch = run_inference(repo_name, issue_number,base_commit,oracle_retrieval_file_path)
        
        # Build the output dictionary
        output_dict = {
            "instance_id": instance_id,
            "model_patch": model_patch,
            "model_name_or_path": "tzanetoast-agents"  # Replace with your actual model name/path if needed
        }
        
        # Append the dictionary as a JSON object to the output JSONL file
        append_dict_to_jsonl(output_dict, output_file)
        


if __name__ == "__main__":
    main()
