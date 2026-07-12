import subprocess
import sys
from pathlib import Path

# Path to requirements.txt
BASE_DIR = Path(__file__).resolve().parent
requirements = BASE_DIR / "requirements.txt"

# Install requirements
print("Checking project dependencies...")
subprocess.check_call([
    sys.executable,
    "-m",
    "pip",
    "install",
    "-r",
    str(requirements)
])

print("Dependencies are ready.")

# Start Flask application
from app import app

if __name__ == "__main__":
    app.run(debug=True)