import logging
import os
import shutil
import uuid
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash
)
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import FileField, SubmitField, MultipleFileField, StringField, PasswordField
from wtforms.validators import InputRequired

from app.services.detector import run_detection
from app.services.review import load_review_report
from app.services.repository import upload_repository

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory store for per-session detection results.
RESULTS_STORE = {}

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'static',
    'file'
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-insecure-key')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DEBUG_MODE = os.environ.get('FLASK_DEBUG', '0') == '1'

TXT_UPLOAD_FOLDER = (
    Path(__file__).resolve().parent.parent
    / "utils"
    / "txtFileUpload"
)

logger.info("Flask app created.")
logger.info("UPLOAD_FOLDER = %s", UPLOAD_FOLDER)
logger.info("Exists? %s", os.path.exists(UPLOAD_FOLDER))


def clear_upload_folders():
    folders = [
        Path(app.config["UPLOAD_FOLDER"]),
        TXT_UPLOAD_FOLDER,
    ]
    for folder in folders:
        if not folder.exists():
            continue
        for file in folder.iterdir():
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)


def get_session_id():
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]


# ============================================================
# Forms
# ============================================================
class UploadFileForm(FlaskForm):
    files = MultipleFileField("Files", validators=[InputRequired()])
    submit = SubmitField("Upload Files")


class RepositoryUploadForm(FlaskForm):
    files = MultipleFileField("Repository Files", validators=[InputRequired()])
    submit = SubmitField("Add to Repository")


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Sign In')


# ============================================================
# Authentication
# ============================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# Routes
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # ---------- MOCK AUTH ----------
        valid_users = {
            'admin': 'admin',
            'instructor': 'instructor',
            'student': 'student'
        }
        if username in valid_users and valid_users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            # Optionally set a role (can be extended later)
            session['role'] = 'Instructor'
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    logger.info("Route accessed: /home (%s)", request.method)
    form = UploadFileForm()

    if form.validate_on_submit():
        logger.info("Upload form validated")
        clear_upload_folders()

        for file in form.files.data:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            logger.info("Saved: %s -> %s", filename, save_path)

        try:
            results = run_detection()
        except Exception:
            logger.exception("run_detection() failed")
            return render_template(
                "error.html",
                message="Something went wrong while analyzing your files. Please try again."
            ), 500

        RESULTS_STORE[get_session_id()] = results

        return render_template(
            "results.html",
            uploaded_files=results["uploaded_files"],
            total_uploaded=results["total_uploaded"],
            total_repository=results["total_repository"],
            results=results["results"]
        )

    if request.method == "POST":
        logger.info("Form errors: %s", form.errors)

    return render_template("index.html", form=form)


@app.route("/dashboard")
@login_required
def dashboard():
    base_dir = Path(__file__).resolve().parent.parent.parent   # project root
    corpus_promoted = base_dir / "corpus" / "promoted"
    corpus_review   = base_dir / "corpus" / "review"

    repo_promoted = 0
    repo_pending  = 0
    if corpus_promoted.exists():
        repo_promoted = len([f for f in corpus_promoted.iterdir() if f.is_file()])
    if corpus_review.exists():
        repo_pending = len([f for f in corpus_review.iterdir() if f.is_file()])

    print("=== DASHBOARD DEBUG ===")
    print("Promoted folder:", corpus_promoted, "->", repo_promoted, "files")
    print("Review folder:  ", corpus_review, "->", repo_pending, "files")

    summary = {
        "documents_analyzed": repo_promoted + repo_pending,
        "flagged_for_review": repo_pending,
        "pending_reviews": repo_pending,
        "repository_size": repo_promoted,
        "documents_analyzed_delta": 0,
        "flagged_for_review_delta": 0,
        "repository_size_delta": 0,
        "pending_reviews_delta": 0,
        "promoted_count": repo_promoted,
        "pending_promotion": repo_pending,
    }

    repo_status = {
        "promoted": repo_promoted,
        "pending_promotion": repo_pending,
        "last_updated": "Now",
    }

    # Pass user info from session for personalised greeting
    user_name = session.get('username', '')
    user_role = session.get('role', 'Instructor')

    return render_template(
        "dashboard.html",
        summary=summary,
        repo_status=repo_status,
        user_name=user_name,
        user_role=user_role
    )


@app.route("/review/<filename>")
@login_required
def review(filename):
    report = load_review_report(filename)
    return render_template("review.html", review=report)


@app.route("/results")
@login_required
def results():
    last_results = RESULTS_STORE.get(get_session_id())
    if last_results is None:
        return redirect(url_for("home"))
    return render_template(
        "results.html",
        uploaded_files=last_results["uploaded_files"],
        total_uploaded=last_results["total_uploaded"],
        total_repository=last_results["total_repository"],
        results=last_results["results"]
    )


@app.route("/repository", methods=["GET", "POST"])
@login_required
def repository():
    form = RepositoryUploadForm()

    if form.validate_on_submit():
        for file in form.files.data:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            logger.info("Repository upload: %s", filename)

        uploaded_files = upload_repository()
        # After a successful upload, we still need to pass the current repository list
        # so the page shows the newly added files.
        # We'll fetch the repository files from the promoted folder.
        base_dir = Path(__file__).resolve().parent.parent.parent
        corpus_promoted = base_dir / "corpus" / "promoted"
        repo_files = []
        if corpus_promoted.exists():
            for f in corpus_promoted.iterdir():
                if f.is_file():
                    repo_files.append({
                        "filename": f.name,
                        "date_added": f.stat().st_mtime,   # you may format this in the template
                    })
        return render_template(
            "repository.html",
            form=form,
            uploaded_files=uploaded_files,
            repository_files=repo_files
        )

    # GET request: show the current repository list
    base_dir = Path(__file__).resolve().parent.parent.parent
    corpus_promoted = base_dir / "corpus" / "promoted"
    repo_files = []
    if corpus_promoted.exists():
        for f in corpus_promoted.iterdir():
            if f.is_file():
                repo_files.append({
                    "filename": f.name,
                    "date_added": f.stat().st_mtime,
                })
    return render_template(
        "repository.html",
        form=form,
        uploaded_files=[],
        repository_files=repo_files
    )


# ============================================================
# Error handlers
# ============================================================
@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", message="An unexpected error occurred. Please try again."), 500


logger.info("main.py finished importing.")

if __name__ == '__main__':
    app.run(debug=DEBUG_MODE)