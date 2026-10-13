import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
requirements = BASE_DIR / "requirements.txt"

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

print("Before importing app")
from app import app
print("After importing app")

if __name__ == "__main__":
    print("About to start Flask...")
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        use_reloader=False
    )
    print("Flask has stopped.")