import base64
import os
import requests

GITHUB_REPO = "os959345/webscrapper"
GITHUB_TOKEN = ""  # <-- Set this securely

GITHUB_API_URL = "https://api.github.com"
GITHUB_BRANCH = "main"

def upload_file_to_github(file_path, repo_path, commit_message):
    """Upload a single file to GitHub repo_path from local file_path"""
    if not GITHUB_TOKEN:
        print("[❌] GitHub token not set")
        return

    url = f"{GITHUB_API_URL}/repos/{GITHUB_REPO}/contents/{repo_path}"

    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Check if file exists to get its SHA
    response = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
    if response.status_code == 200:
        sha = response.json()["sha"]
    else:
        sha = None

    data = {
        "message": commit_message,
        "branch": GITHUB_BRANCH,
        "content": content
    }
    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)

    if response.status_code in [200, 201]:
        print(f"[✅] Uploaded: {repo_path}")
    else:
        print(f"[❌] Failed to upload {repo_path}: {response.status_code} - {response.text}")


def upload_scraped_data_to_github():
    """Uploads CSV, JSON and product images to GitHub"""
    print("\n⬆️ Uploading data to GitHub...")

    base_dir = os.path.abspath("app/data")
    commit_message = "Upload scraped data"

    # Upload CSV and JSON
    for filename in os.listdir(base_dir):
        if filename.endswith(".csv") or filename.endswith(".json"):
            file_path = os.path.join(base_dir, filename)
            repo_path = f"data/{filename}"
            upload_file_to_github(file_path, repo_path, commit_message)

    # Upload all images from product_images/
    images_dir = os.path.join(base_dir, "product_images")
    for root, _, files in os.walk(images_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, base_dir)  # e.g., product_images/abc.jpg
            repo_path = f"data/{relative_path}"
            upload_file_to_github(local_path, repo_path, commit_message)

    print("✅ All data pushed to GitHub.\n")
