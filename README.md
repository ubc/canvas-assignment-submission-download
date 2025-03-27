# Canvas Assignment Submission Downloader
This script downloads all submissions for all assignments from a Canvas course using the Canvas API.

## Prerequisites
Ensure you have Python installed (3.8+ required).

## Setup
1. **Clone this repository** (or place the script in your project folder).
2. **Create a `.env` file** in the same directory as the script and add your Canvas credentials:
   ```ini
   CANVAS_API_URL=https://yourinstitution.instructure.com/
   CANVAS_API_KEY=your_api_key_here
   CANVAS_COURSE_ID=your_course_id
   ```
3. **Set up a virtual environment** (Recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   venv\Scripts\activate  # On Windows
   ```
4. **Install dependencies within the virtual environment**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the script**:
   ```bash
   python index.py
   ```

## How It Works
- The script connects to Canvas using the provided API credentials.
- It retrieves all submissions from published assignments in the course.
- If a submission has an attached file, it downloads it into the `submissions/` directory.
- The script will create the `submissions/` directory if it doesn't exist.

## Configuration Options

### Including All Submission Versions
By default, the script downloads all submission versions for each student. You can control this behavior by changing the `INCLUDE_ALL_SUBMISSIONS` setting:

```python
# Configuration options
INCLUDE_ALL_SUBMISSIONS = True  # Set to False to download only the latest submission
```

- When set to `True`: The script will download every submission version the student has made, organizing them with version numbers in the filename (e.g., `student_name_12345_v1_20240327_123456_assignment.pdf`, `student_name_12345_v2_20240327_124530_assignment.pdf`)
  
- When set to `False`: The script will download only the most recent submission from each student

### Excluding extensions
If you want to filter out certain file extensions, you can specify it as: 
```python
EXCLUDED_EXTENSIONS = {".mp4", ".mov", ".avi"}  # Add any extensions you want to skip
```

## Adjusting `MAX_WORKERS`
`MAX_WORKERS` controls the level of concurrency, which will impact performance:
- **Increasing `MAX_WORKERS`**: Allows more simultaneous downloads, improving speed for large assignments. However, setting it too high may overload the system or Canvas API rate limits.
- **Decreasing `MAX_WORKERS`**: Reduces concurrency, which may help with API throttling but slows down downloads.

## Notes
- Ensure your API token has the necessary permissions to access course submissions.
- Submission downloads that fail are logged in `failed_downloads.txt`.
- Each submission filename includes:
  - Student name
  - Student ID
  - Version number (when `INCLUDE_ALL_SUBMISSIONS` is `True`)
  - Submission timestamp
  - Original filename

## License
This project is licensed under the AGPL-3.0 license License.