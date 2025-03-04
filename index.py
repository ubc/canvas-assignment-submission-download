import os
import requests
import time
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv
from canvasapi import Canvas

# Load environment variables from .env
load_dotenv()

# Canvas API setup
API_URL = os.getenv("CANVAS_API_URL")  # e.g., https://yourinstitution.instructure.com/
API_KEY = os.getenv("CANVAS_API_KEY")
COURSE_ID = os.getenv("CANVAS_COURSE_ID")

canvas = Canvas(API_URL, API_KEY)
course = canvas.get_course(COURSE_ID)
assignments = course.get_assignments()

# Output directory
BASE_DIR = "submissions"
DOWNLOAD_DIR = os.path.join(BASE_DIR, course.name.replace("/", "_"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Ensure submissions directory is gitignored
gitignore_path = ".gitignore"
gitignore_entry = "submissions/\n"
if not os.path.exists(gitignore_path) or gitignore_entry not in open(gitignore_path).read():
    with open(gitignore_path, "a") as gitignore_file:
        gitignore_file.write(gitignore_entry)

# Status file for failed downloads
STATUS_FILE = os.path.join(DOWNLOAD_DIR, "failed_downloads.txt")

def log_failed_download(file_name, url, status_code):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(STATUS_FILE, "a") as f:
        f.write(f"[{timestamp}] Failed: {file_name}, URL: {url}, Status Code: {status_code}\n")

def download_file(url, filename):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    retries = 3
    while retries > 0:
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded: {filename}")
            return
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"Rate limited. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            retries -= 1
        else:
            print(f"Failed to download {filename}: {response.status_code}")
            log_failed_download(filename, url, response.status_code)
            return

def process_submission(submission, assignment_dir):
    time.sleep(0.5)  # Delay to reduce API load
    user = course.get_user(submission.user_id)
    if submission.attachments:
        for attachment in submission.attachments:
            if attachment.filename.lower().endswith(".mp4"):
                print(f"Skipping MP4 file: {attachment.filename}")
                continue  # Skip .mp4 files
            
            file_name = f"{user.name.replace(' ', '_')}_{user.id}_{attachment.filename}"
            file_path = os.path.join(assignment_dir, file_name)

            # Check if file already exists
            if os.path.exists(file_path):
                print(f"File already exists, skipping: {file_name}")
                continue

            file_url = attachment.url
            download_file(file_url, file_path)
    else:
        print(f"No file submission for user {submission.user_id}")


# Download submissions for all PUBLISHED assignments with controlled concurrency
MAX_WORKERS = 10
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = []
    for assignment in assignments:
        # Only process published assignments
        if assignment.published:
            print(f"Processing published assignment: {assignment.name}")
            submissions = assignment.get_submissions()
            assignment_dir = os.path.join(DOWNLOAD_DIR, assignment.name.replace("/", "_"))
            os.makedirs(assignment_dir, exist_ok=True)
            
            for submission in submissions:
                futures.append(executor.submit(process_submission, submission, assignment_dir))
        else:
            print(f"Skipping unpublished assignment: {assignment.name}")
    
    concurrent.futures.wait(futures)

print("Download complete. Check 'failed_downloads.txt' for any failed downloads.")
