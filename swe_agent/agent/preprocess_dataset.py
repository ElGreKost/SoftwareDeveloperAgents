import re
import pandas as pd
from datasets import load_dataset
from dataclasses import dataclass
from pprint import pprint


def get_solved_dataset(
        csv_filepath: str = '/mnt/c/Users/kosti/PycharmProjects/SoftwareDeveloperAgents/swe_agent/agent/solved.csv') -> \
list[dict]:
    csv_df = pd.read_csv(csv_filepath)

    allowed_keys = {
        (row.repo.strip(), str(row.instance_id).strip())
        for _, row in csv_df.iterrows()
    }

    swe_bench_test_dataset = load_dataset("princeton-nlp/SWE-bench", split="test")

    def extract_owner_repo_issue_num(instance_id):
        pattern = r'^(?P<owner_repo>.+)-(?P<issue_num>[^-]+)$'
        match = re.match(pattern, instance_id)
        if not match:
            raise ValueError("Invalid instance_id format")

        owner__repo = match.group("owner_repo")
        issue_num = match.group("issue_num")

        return owner__repo.split("__")[0], owner__repo.split("__")[1], issue_num

    solved_issues: list[dict] = []
    for issue_data in swe_bench_test_dataset:
        owner, repo, issue_num = extract_owner_repo_issue_num(issue_data["instance_id"])
        issue, commit_hash = issue_data["problem_statement"], issue_data["base_commit"]
        gold_file_path = re.findall(r"(?<=diff --git a)\S+", issue_data["patch"])[0]

        for solved_repo, solved_issue_num in allowed_keys:
            if solved_repo == repo and solved_issue_num == issue_num:
                solved_issues.append(
                    dict(owner=owner, repo=repo, issue_num=issue_num, issue_text=issue, commit_hash=commit_hash,
                         gold_file_path=gold_file_path)
                )

    return solved_issues
