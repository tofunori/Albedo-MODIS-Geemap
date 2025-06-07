"""
Deployment script for automatic CSV upload to GitHub
Runs after analysis to update online data sources
"""

import os
import subprocess
import shutil
from pathlib import Path
import argparse

def upload_csv_files_to_github(commit_message="Update analysis results"):
    """
    Upload CSV files to GitHub repository
    
    Args:
        commit_message: Git commit message
    """
    print("🚀 Starting CSV upload to GitHub...")
    
    csv_files = [
        "../outputs/csv/athabasca_mcd43a3_results.csv",
        "../outputs/csv/athabasca_melt_season_results.csv", 
        "../outputs/csv/athabasca_hypsometric_results.csv",
        "../outputs/csv/athabasca_mcd43a3_spectral_data.csv",
        "../outputs/csv/athabasca_melt_season_data.csv",
        "../outputs/csv/athabasca_hypsometric_data.csv"
    ]
    
    # Check which files exist
    existing_files = []
    for file_path in csv_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
            print(f"✅ Found: {file_path}")
        else:
            print(f"⚠️ Missing: {file_path}")
    
    if not existing_files:
        print("❌ No CSV files found to upload")
        return False
    
    try:
        # Check if we're in a git repository
        result = subprocess.run(['git', 'status'], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("❌ Not in a git repository")
            return False
        
        # Add CSV files to git
        for file_path in existing_files:
            subprocess.run(['git', 'add', file_path], check=True)
            print(f"📝 Added to git: {file_path}")
        
        # Check if there are changes to commit
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True, check=False)
        if result.returncode == 0:
            print("ℹ️ No changes to commit")
            return True
        
        # Commit changes
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        print(f"💾 Committed changes: {commit_message}")
        
        # Push to remote
        subprocess.run(['git', 'push'], check=True)
        print("🌐 Pushed to GitHub successfully!")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Git operation failed: {e}")
        return False

def create_github_actions_workflow():
    """
    Create GitHub Actions workflow for automatic deployment
    """
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    workflow_content = """name: Deploy Streamlit App

on:
  push:
    branches: [ main ]
    paths: 
      - 'outputs/csv/*.csv'
      - 'streamlit_dashboard.py'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install streamlit requests pandas plotly numpy
    
    - name: Test Streamlit app
      run: |
        streamlit run streamlit_dashboard.py --server.headless true &
        sleep 10
        curl -f http://localhost:8501 || exit 1
        
    - name: Trigger Streamlit Cloud deployment
      run: |
        echo "CSV files updated - Streamlit Cloud will auto-deploy"
"""
    
    workflow_file = workflow_dir / "deploy-streamlit.yml"
    with open(workflow_file, 'w') as f:
        f.write(workflow_content)
    
    print(f"✅ Created GitHub Actions workflow: {workflow_file}")

def main():
    """
    Main deployment function
    """
    parser = argparse.ArgumentParser(description='Deploy Streamlit dashboard')
    parser.add_argument('--upload', action='store_true', help='Upload CSV files to GitHub')
    parser.add_argument('--create-workflow', action='store_true', help='Create GitHub Actions workflow')
    parser.add_argument('--message', default='Update analysis results', help='Git commit message')
    
    args = parser.parse_args()
    
    if args.create_workflow:
        create_github_actions_workflow()
    
    if args.upload:
        success = upload_csv_files_to_github(args.message)
        if success:
            print("🎉 Deployment preparation complete!")
            print("📊 Your Streamlit dashboard will update automatically")
        else:
            print("❌ Deployment failed")
            return 1
    
    if not args.upload and not args.create_workflow:
        print("Usage:")
        print("  python deploy_streamlit.py --upload")
        print("  python deploy_streamlit.py --create-workflow") 
        print("  python deploy_streamlit.py --upload --message 'Updated with latest analysis'")
    
    return 0

if __name__ == "__main__":
    exit(main())