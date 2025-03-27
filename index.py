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

# Configuration options
INCLUDE_ALL_SUBMISSIONS = True  # Set to False to download only the latest submission
EXCLUDED_EXTENSIONS = {".mp4"} 

canvas = Canvas(API_URL, API_KEY)
course = canvas.get_course(COURSE_ID)
assignments = course.get_assignments()

# Output directory
BASE_DIR = "submissions"
DOWNLOAD_DIR = os.path.join(BASE_DIR, course.name.replace("/", "_"))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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
            return True
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"Rate limited. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)
            retries -= 1
        else:
            print(f"Failed to download {filename}: {response.status_code}")
            log_failed_download(filename, url, response.status_code)
            return False
    return False

def get_submission_detail(assignment_id, user_id):
    """Fetch the latest submission details for a specific user and assignment"""
    url = f"{API_URL}/api/v1/courses/{COURSE_ID}/assignments/{assignment_id}/submissions/{user_id}"
    params = {"include[]": "attachments"}
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch submission details: {response.status_code}")
        return None

def get_all_submission_versions(assignment_id, user_id):
    """Fetch all submission versions for a specific user and assignment"""
    url = f"{API_URL}/api/v1/courses/{COURSE_ID}/assignments/{assignment_id}/submissions/{user_id}"
    params = {"include[]": "submission_history"}
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch submission versions: {response.status_code}")
        return None

def format_date(date_str):
    """Format date string from Canvas API"""
    if not date_str:
        return "no_date"
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y%m%d_%H%M%S")
    except ValueError:
        return "invalid_date"

def process_submission(submission, assignment_dir, assignment_id):
    """Process student submission(s) based on configuration"""
    time.sleep(0.5)  # Delay to reduce API load
    
    # Get the user information
    try:
        user = course.get_user(submission.user_id)
        user_name = user.name.replace(' ', '_')
        user_id = user.id
    except Exception as e:
        print(f"Error fetching user info for user ID {submission.user_id}: {e}")
        user_name = f"user_{submission.user_id}"
        user_id = submission.user_id
    
    if INCLUDE_ALL_SUBMISSIONS:
        # Get all submission versions for this student
        all_versions = get_all_submission_versions(assignment_id, user_id)
        
        if not all_versions or 'submission_history' not in all_versions:
            print(f"No submission history available for {user_name} (ID: {user_id})")
            
            # Try processing just the current submission if it has attachments
            if hasattr(submission, 'attachments') and submission.attachments:
                process_attachments(submission.attachments, user_name, user_id, 1, 
                                  format_date(submission.submitted_at), assignment_dir)
            return
        
        # Process each version in the submission history
        submission_history = all_versions['submission_history']
        
        print(f"Found {len(submission_history)} submission versions for {user_name}")
        
        for version_idx, version in enumerate(submission_history):
            version_num = version_idx + 1
            submitted_at = format_date(version.get('submitted_at', None))
            
            # Check if this version has attachments
            if 'attachments' in version and version['attachments']:
                process_attachments(version['attachments'], user_name, user_id, 
                                  version_num, submitted_at, assignment_dir)
            else:
                print(f"No attachments in version {version_num} for {user_name} (ID: {user_id})")
    else:
        # Process only the latest submission
        version_num = 1  # Always mark as version 1 for latest-only mode
        submitted_at = format_date(getattr(submission, 'submitted_at', None))
        
        # Get the current submission directly from the API to ensure we have the attachments
        latest_submission = get_submission_detail(assignment_id, user_id)
        
        if latest_submission and 'attachments' in latest_submission and latest_submission['attachments']:
            print(f"Processing latest submission for {user_name} (ID: {user_id})")
            process_attachments(latest_submission['attachments'], user_name, user_id, 
                              version_num, submitted_at, assignment_dir)
        else:
            print(f"No attachments in latest submission for {user_name} (ID: {user_id})")

def process_attachments(attachments, user_name, user_id, version_num, submitted_at, assignment_dir):
    """Process and download attachments for a submission version"""
    files_downloaded = 0
    
    for attachment in attachments:
        # Get the file extension
        file_ext = os.path.splitext(attachment['filename'])[1].lower() if 'filename' in attachment else ""
        
        if file_ext in EXCLUDED_EXTENSIONS:
            print(f"Skipping file (excluded type): {attachment.get('filename', 'unknown')}")
            continue
        
        # Create a descriptive filename including version and timestamp
        file_name = f"{user_name}_{user_id}_v{version_num}_{submitted_at}_{attachment.get('filename', 'unnamed')}"
        file_path = os.path.join(assignment_dir, file_name)
        
        # Check if file already exists
        if os.path.exists(file_path):
            print(f"File already exists, skipping: {file_name}")
            continue
        
        # Download the file
        if download_file(attachment.get('url', None), file_path):
            files_downloaded += 1
    
    if files_downloaded > 0:
        print(f"Downloaded {files_downloaded} files for version {version_num} ({user_name})")

# Filter only assignments (excluding quizzes)
valid_assignments = [
    assignment for assignment in assignments
    if "online_quiz" not in assignment.submission_types  # Exclude quizzes
]

# Download submissions for all PUBLISHED assignments with controlled concurrency
MAX_WORKERS = 10 # set appropriate number of workers based on API rate limits
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = []
    
    for assignment in valid_assignments:
        # Only process published assignments
        if assignment.published:
            print(f"\nProcessing published assignment: {assignment.name} (ID: {assignment.id})")
            print(f"Mode: {'All submission versions' if INCLUDE_ALL_SUBMISSIONS else 'Latest submissions only'}")
            
            # Create directory for this assignment
            assignment_dir = os.path.join(DOWNLOAD_DIR, f"{assignment.name.replace('/', '_')}_{assignment.id}")
            os.makedirs(assignment_dir, exist_ok=True)
            
            # Get all submissions for this assignment
            try:
                submissions = assignment.get_submissions()
                print(f"Found {len(list(submissions))} student submissions for assignment {assignment.name}")
                
                for submission in submissions:
                    futures.append(
                        executor.submit(process_submission, submission, assignment_dir, assignment.id)
                    )
            except Exception as e:
                print(f"Error retrieving submissions for assignment {assignment.name}: {e}")
        else:
            print(f"Skipping unpublished assignment: {assignment.name}")
    
    # Wait for all tasks to complete
    for future in concurrent.futures.as_completed(futures):
        try:
            future.result()
        except Exception as e:
            print(f"An error occurred during processing: {e}")

print("\nDownload complete. Check 'failed_downloads.txt' for any failed downloads.")