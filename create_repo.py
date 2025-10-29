#!/usr/bin/env python3
"""


Requirements:
    pip install PyGithub

Environment Variables:
    GITHUB_TOKEN - GitHub Personal Access Token (from Secrets Manager)
    OWNER_NAME   - GitHub organization name OR user login
    REPO_NAME    - Name of the new repository
    BRANCH_NAMES - Comma-separated branches (default: dev,qa,main)
    USERS        - Comma-separated GitHub usernames for team membership
"""
import os
import time
import base64
from github import Github, Auth
from github.GithubException import GithubException

def create_branches(repo):
    """
    Creates additional branches in the repository.
    Default branches: dev, qa, main
    """
    branch_names_env = os.getenv("BRANCH_NAMES", "dev,qa")
    branch_names = [b.strip() for b in branch_names_env.split(",") if b.strip()]
    
    if not branch_names:
        print(" No branches provide to create")
        return
    
    print(f"\n Creating branches: {', '.join(branch_names)}")
    
    try:
        default_branch = repo.default_branch
        source_branch = repo.get_branch(default_branch)
        source_sha = source_branch.commit.sha
        
        print(f" Using '{default_branch}' (SHA: {source_sha[:7]}) as base branch")
        time.sleep(2)
        
        for branch_name in branch_names:
            try:
                repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=source_sha
                )
                print(f"   Branch '{branch_name}' created successfully")
            except GithubException as e:
                if e.status == 422:
                    print(f"   Branch '{branch_name}' already exists")
                else:
                    print(f"   Failed to create branch '{branch_name}': {e.data if hasattr(e,'data') else e}")
        
        print(f" Branch creation completed!")
        
    except GithubException as e:
        print(f" Error during branch creation: {e.data if hasattr(e,'data') else e}")


def create_teams_and_add_members(org, repo, users):
    """
    Creates teams l1 and l2, adds members, and grants repository access.
    - l1: First user only, push access
    - l2: All users, push access
    """
    if not users:
        print("\n No users provided. Skipping team creation.")
        return
    
    print(f"\n Creating teams and adding members...")
    
    teams_config = [
        {'name': 'l1', 'members': [users[0]] if users else []},
        {'name': 'l2', 'members': users}
    ]
    
    for team_config in teams_config:
        team_name = team_config['name']
        members = team_config['members']
        
        try:
            # Try to get existing team
            team = None
            for t in org.get_teams():
                if t.name.lower() == team_name.lower():
                    team = t
                    print(f"  ℹ️ Team '{team_name}' already exists")
                    break
            
            # Create team if it doesn't exist
            if not team:
                team = org.create_team(
                    name=team_name,
                    privacy="closed"
                )
                print(f"   Team '{team_name}' created")
            
            # Grant team access to repository
            team.add_to_repos(repo)
            team.set_repo_permission(repo, "push")
            print(f"   Team '{team_name}' granted push access to repository")
            
            # Add members to team
            for username in members:
                try:
                    team.add_membership(username, role="member")
                    print(f"   Added user '{username}' to team '{team_name}'")
                except GithubException as e:
                    print(f"   Failed to add '{username}' to '{team_name}': {e.data if hasattr(e,'data') else e}")
        
        except GithubException as e:
            print(f"   Failed to create/configure team '{team_name}': {e.data if hasattr(e,'data') else e}")


def add_codeowners(repo, org_name):
    """
    Adds CODEOWNERS file with branch-specific ownership rules.
    """
    print(f"\n Adding CODEOWNERS file...")
    
    codeowners_content = f"""# Branch-specific ownership
/dev/* @{org_name}/l1
/qa/* @{org_name}/l1 @{org_name}/l2
/main/* @{org_name}/l2
"""
    
    try:
        default_branch = repo.default_branch
        
        # Create or update CODEOWNERS file
        file_path = ".github/CODEOWNERS"
        try:
            # Try to get existing file
            contents = repo.get_contents(file_path, ref=default_branch)
            repo.update_file(
                path=file_path,
                message="Update CODEOWNERS for branch-specific reviews",
                content=codeowners_content,
                sha=contents.sha,
                branch=default_branch
            )
            print(f"   CODEOWNERS file updated")
        except GithubException:
            # File doesn't exist, create it
            repo.create_file(
                path=file_path,
                message="Add CODEOWNERS for branch-specific reviews",
                content=codeowners_content,
                branch=default_branch
            )
            print(f"   CODEOWNERS file created")
    
    except GithubException as e:
        print(f"   Failed to add CODEOWNERS: {e.data if hasattr(e,'data') else e}")


def add_ci_workflow(repo):
    """
    Adds GitHub Actions CI workflow to all branches.
    """
    print(f"\n Adding CI workflow...")
    
    workflow_content = """name: build

on:
  push:
    branches: ['**']
  pull_request:
    branches: ['**']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Run build
        run: |
          echo "🔨 Build started"
          echo "Running tests..."
          # Add your actual build/test commands here
          echo " Build completed successfully"
      
      - name: Build status
        run: echo "Build passed for commit ${{ github.sha }}"
"""
    
    try:
        default_branch = repo.default_branch
        file_path = ".github/workflows/build.yml"
        
        # Create workflow file on default branch
        try:
            contents = repo.get_contents(file_path, ref=default_branch)
            repo.update_file(
                path=file_path,
                message="Update GitHub Actions build workflow",
                content=workflow_content,
                sha=contents.sha,
                branch=default_branch
            )
            print(f"   CI workflow updated on '{default_branch}'")
        except GithubException:
            repo.create_file(
                path=file_path,
                message="Add GitHub Actions build workflow",
                content=workflow_content,
                branch=default_branch
            )
            print(f"   CI workflow added to '{default_branch}'")
        
        # Sync to other branches (dev, qa)
        time.sleep(2)
        for branch_name in ['dev', 'qa']:
            try:
                branch = repo.get_branch(branch_name)
                # Get the file from default branch
                file_content = repo.get_contents(file_path, ref=default_branch)
                
                # Create or update on target branch
                try:
                    existing = repo.get_contents(file_path, ref=branch_name)
                    repo.update_file(
                        path=file_path,
                        message=f"Sync CI workflow to {branch_name}",
                        content=file_content.decoded_content.decode('utf-8'),
                        sha=existing.sha,
                        branch=branch_name
                    )
                except GithubException:
                    repo.create_file(
                        path=file_path,
                        message=f"Add CI workflow to {branch_name}",
                        content=file_content.decoded_content.decode('utf-8'),
                        branch=branch_name
                    )
                print(f"   CI workflow synced to '{branch_name}'")
            except GithubException as e:
                print(f"   Could not sync to '{branch_name}': {e.data if hasattr(e,'data') else e}")
    
    except GithubException as e:
        print(f"  ❌ Failed to add CI workflow: {e.data if hasattr(e,'data') else e}")


def enable_branch_protection(repo):
    """
    Enables branch protection rules for dev, qa, and main branches.
    """
    print(f"\n Enabling branch protection...")
    
    protections = [
        {"branch": "dev", "review_count": 1, "code_owner": True},
        {"branch": "qa", "review_count": 1, "code_owner": True},
        {"branch": "main", "review_count": 2, "code_owner": True}
    ]
    
    for protection in protections:
        branch_name = protection["branch"]
        try:
            branch = repo.get_branch(branch_name)
            branch.edit_protection(
                strict=True,
                contexts=["build"],
                enforce_admins=True,
                require_code_owner_reviews=protection["code_owner"],
                required_approving_review_count=protection["review_count"]
            )
            print(f"   Branch protection enabled for '{branch_name}' ({protection['review_count']} reviews required)")
        except GithubException as e:
            if e.status == 404:
                print(f"   Branch '{branch_name}' not found, skipping protection")
            else:
                print(f"   Failed to protect '{branch_name}': {e.data if hasattr(e,'data') else e}")


def main():
    github_token = os.getenv("GITHUB_TOKEN")
    owner_name = os.getenv("OWNER_NAME")
    repo_name = os.getenv("REPO_NAME")
    users_env = os.getenv("USERS", "")

    if not all([github_token, owner_name, repo_name]):
        print(" Missing environment variables: GITHUB_TOKEN, OWNER_NAME, REPO_NAME")
        return

    users = [u.strip() for u in users_env.split(",") if u.strip()] if users_env else []

    print(f" Connecting to GitHub with token...")
    g = Github(auth=Auth.Token(github_token))
    
    authenticated_user = g.get_user()
    is_organization = False
    
    # Try as organization first
    try:
        owner = g.get_organization(owner_name)
        owner_type = "organization"
        is_organization = True
        print(f" Owner detected as organization: {owner_name}")
        target = owner
    except GithubException:
        try:
            owner = g.get_user(owner_name)
            owner_type = "user"
            print(f" Owner detected as user: {owner_name}")
            
            if owner.login != authenticated_user.login:
                print(f" Cannot create repository for user '{owner_name}' - token belongs to '{authenticated_user.login}'")
                return
            
            target = authenticated_user
        except GithubException as e:
            print(f" Failed to access owner '{owner_name}': {e.data if hasattr(e,'data') else e}")
            return

    # Check if repo already exists
    try:
        existing_repos = [r.name for r in target.get_repos()]
        if repo_name in existing_repos:
            print(f" Repository '{repo_name}' already exists under {owner_type} '{owner_name}'. Skipping creation.")
            return
    except GithubException as e:
        print(f" Could not check existing repositories: {e.data if hasattr(e,'data') else e}")

    # Create repository
    try:
        repo = target.create_repo(
            name=repo_name,
            description=f"Repository '{repo_name}' created automatically via CodeBuild script.",
            private=False,
            auto_init=True
        )
        print(f" Repository '{repo_name}' created successfully under {owner_type} '{owner_name}'")
        print(f" Repository URL: {repo.html_url}")
        
        # Wait for repository initialization
        time.sleep(3)
        
        # Create additional branches
        create_branches(repo)
        
        # Organization-specific features
        if is_organization:
            # Create teams and add members
            if users:
                create_teams_and_add_members(owner, repo, users)
            
            # Add CODEOWNERS file
            add_codeowners(repo, owner_name)
        else:
            print("\n Teams and CODEOWNERS are only available for organizations")
        
        # Add CI workflow (works for both org and user)
        add_ci_workflow(repo)
        
        # Enable branch protection (works for both org and user)
        enable_branch_protection(repo)
        
        print("\n Repository setup completed successfully!")
        
    except GithubException as e:
        print(f" Failed to create repository: {e.data if hasattr(e,'data') else e}")

if __name__ == "__main__":
    main()