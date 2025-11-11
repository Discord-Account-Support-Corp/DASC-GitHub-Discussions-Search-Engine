"""
Discord Account Support Corp — Verified Answers Indexer
-------------------------------------------------------
Indexes README.md and "verified answer" files from all repositories
in your GitHub organization into a Meilisearch instance.

Usage:
    1. Set your GitHub token and Meilisearch credentials:
        export GITHUB_TOKEN="ghp_yourtoken"
        export MEILI_URL="http://localhost:7700"
        export MEILI_KEY="masterKey"

    2. Run:
        python scripts/index_verified_answers.py
"""

import os
import re
import base64
import requests
from meilisearch import Client


# --- Configuration ---
ORG = "Discord-Account-Support-Corp"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MEILI_URL = os.getenv("MEILI_URL", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_KEY", "masterKey")
INDEX_NAME = "verified_answers"

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}


# --- Helpers ---------------------------------------------------------------

def get_repos(org: str):
    """Fetch repositories in the given GitHub organization."""
    url = f"https://api.github.com/orgs/{org}/repos?per_page=100&type=public"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return [repo["name"] for repo in res.json()]


def get_file_content(org: str, repo: str, path: str) -> str:
    """Fetch a file's content from GitHub and decode it."""
    url = f"https://api.github.com/repos/{org}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return ""
    data = res.json()
    if "content" in data:
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    return ""


def get_readme(org: str, repo: str) -> str:
    """Fetch the README.md from the repo."""
    url = f"https://api.github.com/repos/{org}/{repo}/readme"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return ""
    data = res.json()
    if "content" in data:
        return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    return ""


def extract_verified_links(readme_text: str):
    """
    Extract 'verified answer' entries from README.
    Format expected:
        ✅ **Title Here** → `path/to/file.md`
    """
    pattern = r"✅\s+\*\*(.+?)\*\*.*?→\s*`([^`]+)`"
    return re.findall(pattern, readme_text)


# --- Main Indexing Logic ---------------------------------------------------

def index_verified_answers():
    client = Client(MEILI_URL, MEILI_KEY)
    index = client.index(INDEX_NAME)

    all_docs = []

    repos = get_repos(ORG)
    print(f"Found {len(repos)} repositories in {ORG}")

    for repo in repos:
        print(f"→ Checking {repo} ...")
        readme = get_readme(ORG, repo)
        if not readme:
            continue

        verified_links = extract_verified_links(readme)
        for title, filepath in verified_links:
            content = get_file_content(ORG, repo, filepath)
            if not content:
                continue

            doc = {
                "repo": repo,
                "file": filepath,
                "title": title.strip(),
                "verified": True,
                "content": content,
                "url": f"https://github.com/{ORG}/{repo}/blob/main/{filepath}"
            }
            all_docs.append(doc)

    if not all_docs:
        print("No verified answers found.")
        return

    print(f"Indexing {len(all_docs)} verified answers to Meilisearch...")
    index.add_documents(all_docs)
    print("✅ Indexing complete!")


# --- Entry Point -----------------------------------------------------------

def main():
    if not GITHUB_TOKEN:
        raise EnvironmentError("Missing GITHUB_TOKEN environment variable.")
    index_verified_answers()


if __name__ == "__main__":
    main()
