from flask import Flask, jsonify, send_from_directory
import os

app = Flask(__name__)
APP_FOLDER = 'hosted_apps'  # Folder where your app files are stored

# List of apps
APPS = [
    {
        "name": "Reminder Timer",
        "description": "Set a timer with a custom message.",
        "category": "official",
        "filename": "reminder_timer.py"
    },
    {
        "name": "To-Do List",
        "description": "Organize your tasks and check them off.",
        "category": "official",
        "filename": "todo_list.py"
    },
    {
        "name": "Weather Check",
        "description": "Check local weather from an API.",
        "category": "community",
        "filename": "weather_check.py"
    },
    {
        "name": "Meme Generator",
        "description": "Make random meme captions (unapproved).",
        "category": "unapproved",
        "filename": "meme_generator.py"
    }
]

@app.route('/apps')
def get_apps():
    return jsonify(APPS)

@app.route('/download/<filename>')
def download_file(filename):
    # Safety check: avoid directory traversal attacks
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    return send_from_directory(APP_FOLDER, filename)

if __name__ == '__main__':
    os.makedirs(APP_FOLDER, exist_ok=True)  # Ensure folder exists
    app.run(debug=True)
