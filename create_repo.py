#!/usr/bin/env python3
"""
Simple script to create a new GitHub repository inside an organization.
Run this in CodeBuild or locally.

Requirements:
    pip install PyGithub

Environment Variables (required):
    GITHUB_TOKEN  - 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
    ORG_NAME      - Adityansh9109
    REPO_NAME     - democodebuild1
"""

import os
from github import Github

def main():
    # Read environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    org_name = os.getenv("ORG_NAME")
    repo_name = os.getenv("REPO_NAME")

    if not all([github_token, org_name, repo_name]):
        print("❌ Missing one or more required environment variables: GITHUB_TOKEN, ORG_NAME, REPO_NAME")
        return

    print(f"🔐 Connecting to GitHub organization: {org_name}")
    g = Github(github_token)

    try:
        org = g.get_organization(org_name)
    except Exception as e:
        print(f"❌ Failed to access organization '{org_name}': {e}")
        return

    try:
        print(f"🚀 Creating new repository: {repo_name}")
        repo = org.create_repo(
            name=repo_name,
            description=f"Repository '{repo_name}' created automatically via CodeBuild script.",
            private=True,
            auto_init=True  # creates README.md automatically
        )
        print(f"✅ Repository '{repo_name}' created successfully in organization '{org_name}'")
        print(f"🔗 Repository URL: {repo.html_url}")
    except Exception as e:
        print(f"❌ Failed to create repository: {e}")

if __name__ == "__main__":
    main()
