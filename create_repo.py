#!/usr/bin/env python3
"""
Creates a new GitHub repository inside an organization.
Designed to run in AWS CodeBuild.

Requirements:
    pip install PyGithub

Environment Variables (from CodeBuild):
    GITHUB_TOKEN - GitHub Personal Access Token (from Secrets Manager, key "GITHUB_TOKEN")
    ORG_NAME     - GitHub organization name
    REPO_NAME    - Name of the new repository
"""

import os
from github import Github, Auth

def main():
    github_token = os.getenv("GITHUB_TOKEN")
    org_name = os.getenv("ORG_NAME")
    repo_name = os.getenv("REPO_NAME")

    if not all([github_token, org_name, repo_name]):
        print("❌ Missing required environment variables: GITHUB_TOKEN, ORG_NAME, REPO_NAME")
        return

    print(f"🔐 Connecting to GitHub organization: {org_name}")
    g = Github(auth=Auth.Token(github_token))  # Correct authentication

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
            auto_init=True  # Creates README.md
        )
        print(f"✅ Repository '{repo_name}' created successfully in org '{org_name}'")
        print(f"🔗 Repository URL: {repo.html_url}")
    except Exception as e:
        print(f"❌ Failed to create repository: {e}")

if __name__ == "__main__":
    main()
