#!/usr/bin/env python3
"""
Creates a new GitHub repository either in a user account or organization.
Designed to run inside AWS CodeBuild.

Requirements:
    pip install PyGithub

Environment Variables:
    GITHUB_TOKEN - GitHub Personal Access Token (from Secrets Manager)
    OWNER_NAME   - GitHub organization name OR user login
    REPO_NAME    - Name of the new repository
"""
import os
from github import Github, Auth
from github.GithubException import GithubException

def main():
    github_token = os.getenv("GITHUB_TOKEN")
    owner_name = os.getenv("OWNER_NAME")
    repo_name = os.getenv("REPO_NAME")

    if not all([github_token, owner_name, repo_name]):
        print("❌ Missing environment variables: GITHUB_TOKEN, OWNER_NAME, REPO_NAME")
        return

    print(f"🔐 Connecting to GitHub with token...")
    g = Github(auth=Auth.Token(github_token))
    
    # Get authenticated user
    authenticated_user = g.get_user()
    
    # Try as organization first
    try:
        owner = g.get_organization(owner_name)
        owner_type = "organization"
        print(f"✅ Owner detected as organization: {owner_name}")
        target = owner
    except GithubException:
        try:
            owner = g.get_user(owner_name)
            owner_type = "user"
            print(f"✅ Owner detected as user: {owner_name}")
            
            # For user accounts, we need to use the authenticated user
            if owner.login != authenticated_user.login:
                print(f"❌ Cannot create repository for user '{owner_name}' - token belongs to '{authenticated_user.login}'")
                return
            
            target = authenticated_user  # Use authenticated user for repo creation
        except GithubException as e:
            print(f"❌ Failed to access owner '{owner_name}': {e.data if hasattr(e,'data') else e}")
            return

    # Check if repo already exists
    try:
        existing_repos = [r.name for r in target.get_repos()]
        if repo_name in existing_repos:
            print(f"⚠️ Repository '{repo_name}' already exists under {owner_type} '{owner_name}'. Skipping creation.")
            return
    except GithubException as e:
        print(f"⚠️ Could not check existing repositories: {e.data if hasattr(e,'data') else e}")

    # Create repository
    try:
        repo = target.create_repo(
            name=repo_name,
            description=f"Repository '{repo_name}' created automatically via CodeBuild script.",
            private=True,
            auto_init=True
        )
        print(f"🚀 Repository '{repo_name}' created successfully under {owner_type} '{owner_name}'")
        print(f"🔗 Repository URL: {repo.html_url}")
    except GithubException as e:
        print(f"❌ Failed to create repository: {e.data if hasattr(e,'data') else e}")

if __name__ == "__main__":
    main()
