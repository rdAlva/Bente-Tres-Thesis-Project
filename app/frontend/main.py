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
from wtforms.validators import InputRequired, Email

from supabase import create_client, Client


from app.services.detector import run_detection
from app.services.review import load_review_report
from app.services.repository import upload_repository
from app.nlp.preprocessing import preprocess_text

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

REVIEW_FOLDER = (
    Path(__file__).resolve().parent.parent.parent
    / "corpus"
    / "review"
)

PROMOTED_FOLDER = (
    Path(__file__).resolve().parent.parent.parent
    / "corpus"
    / "promoted"
)

PROCESSED_FOLDER = (
    Path(__file__).resolve().parent.parent.parent
    / "corpus"
    / "processed"
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
    email = StringField(
        "Email",
        validators=[
            InputRequired(message="Email is required."),
            Email(message="Please enter a valid email address.")
        ]
    )
    password = PasswordField(
        "Password",
        validators=[
            InputRequired(message="Password is required.")
        ]
    )
    submit = SubmitField("Sign In")
class RegisterForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            InputRequired(message="Email is required."),
            Email(message="Please enter a valid email address.")
        ]
    )
    password = PasswordField(
        "Password",
        validators=[
            InputRequired(message="Password is required.")
        ]
    )

    submit = SubmitField("Sign Up")
    
# ============================================================
# Supabase Settings
# ============================================================
app.secret_key = "supersecretkey"  # Replace with a secure key in production

SUPABASE_URL = "https://xtwdtizzumzahucsbpyc.supabase.co"
SUPABASE_KEY = "sb_publishable_Ri2NBu5O4D9lkVxDlJYxMg_j6LYnzlT"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
@app.route('/')
def home_login():
    if "user" in session:
        return redirect(url_for("home"))

    return redirect(url_for("login"))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        password = form.password.data
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            if response.user:
                flash(
                    "Registration successful! "
                    "Please check your email to verify your account.",
                    "success"
                )
                return redirect(url_for("login"))
            flash(
                "Registration failed. Please try again.",
                "danger"
            )
        except Exception as e:
            print("REGISTRATION ERROR:", repr(e))

            flash(
                f"Registration failed: {str(e)}",
                "danger"
            )
    return render_template("register.html", form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip()
        password = form.password.data
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            if response.user:
                session['logged_in'] = True
                session['user'] = response.user.email
                flash(
                    f"Welcome back, {response.user.email}!",
                    "success"
                )
                return redirect(url_for("home"))
            flash(
                "Invalid email or password.",
                "danger"
            )
        except Exception as e:
            print("LOGIN ERROR:", repr(e))

            flash(
                "Invalid email or password.",
                "danger"
            )
    return render_template("login.html", form=form)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash("Please enter your email.", "danger")
            return redirect(url_for('forgot_password'))
        try:
            reset_url = url_for(
                'reset_password',
                _external=True
            )
            print("RESET REDIRECT URL:", reset_url)
            supabase.auth.reset_password_for_email(
                email,
                options={
                    "redirect_to": reset_url
                }
            )
            flash(
                "If an account exists with that email, "
                "a password reset link has been sent.",
                "success"
            )
            return redirect(url_for('login'))
        except Exception as e:
            print("SUPABASE RESET ERROR:", repr(e))
            flash(
                f"Password reset failed: {str(e)}",
                "danger"
            )
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')
  
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():

    if request.method == 'POST':

        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        access_token = request.form.get('access_token')
        refresh_token = request.form.get('refresh_token')

        if not access_token or not refresh_token:
            flash(
                "Invalid or expired password reset link.",
                "danger"
            )
            return redirect(url_for('forgot_password'))
        if not password or not confirm_password:
            flash(
                "Please enter and confirm your new password.",
                "danger"
            )
            return redirect(url_for('reset_password'))
        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "danger"
            )
            return redirect(url_for('reset_password'))
        try:
            supabase.auth.set_session(
                access_token,
                refresh_token
            )
            supabase.auth.update_user({
                "password": password
            })
            flash(
                "Password reset successful! Please log in.",
                "success"
            )
            return redirect(url_for('login'))
        except Exception as e:
            print("PASSWORD RESET ERROR:", repr(e))
            flash(
                "Unable to reset your password. "
                "The reset link may have expired.",
                "danger"
            )
            return redirect(url_for('forgot_password'))
    return render_template('reset_password.html')

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

        threshold = float(request.form.get("threshold", 0.30))
        logger.info("Selected threshold: %.2f", threshold)

        try:
            results = run_detection(threshold)
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

@app.route("/review/<filename>/dismiss", methods=["POST"])
@login_required
def dismiss_flag(filename):
    txt_source = REVIEW_FOLDER / filename
    txt_destination = PROMOTED_FOLDER / filename
    pdf_name = Path(filename).stem + ".pdf"
    pdf_source = REVIEW_FOLDER / pdf_name
    pdf_destination = PROMOTED_FOLDER / pdf_name
    moved_successfully = False

    try:
        # ----------------------------------------------
        # Move TXT from review -> promoted
        # ----------------------------------------------
        if txt_source.exists():

            shutil.move(
                str(txt_source),
                str(txt_destination)
            )

            print(f"Promoted TXT: {filename}")

            # ------------------------------------------
            # Create persistent processed copy
            # ------------------------------------------

            PROCESSED_FOLDER.mkdir(
                parents=True,
                exist_ok=True
            )

            processed_text = preprocess_text(
                txt_destination
            )

            processed_file = PROCESSED_FOLDER / filename

            processed_file.write_text(
                processed_text,
                encoding="utf-8"
            )

            print(f"Processed TXT: {filename}")

        # ----------------------------------------------
        # Move PDF from review -> promoted
        # ----------------------------------------------

        if pdf_source.exists():
            shutil.move(
                str(pdf_source),
                str(pdf_destination)
            )
            print(f"Promoted PDF: {pdf_name}")

        moved_successfully = True
        flash(
            "Document promoted to repository.",
            "success"
        )

    except Exception as e:
        logger.exception(e)
        flash(
            "Unable to move the document.",
            "danger"
        )

    # ----------------------------------------------
    # Remove promoted document from current results
    # ----------------------------------------------

    if moved_successfully:
        sid = get_session_id()
        if sid in RESULTS_STORE:
            session_results = RESULTS_STORE[sid]
            session_results["uploaded_files"] = [
                f
                for f in session_results["uploaded_files"]
                if f != filename
            ]

            session_results["results"] = [
                r
                for r in session_results["results"]
                if r["uploaded_filename"] != filename
            ]

            session_results["total_uploaded"] = len(
                session_results["uploaded_files"]
            )
    return redirect(url_for("results"))

@app.route("/review/<filename>/confirm", methods=["POST"])
@login_required
def confirm_flag(filename):
    """
    Instructor confirmed plagiarism.
    Leave files in corpus/review.
    """

    flash("Document confirmed as flagged.", "warning")
    sid = get_session_id()
    if sid in RESULTS_STORE:

        session_results = RESULTS_STORE[sid]

        session_results["uploaded_files"] = [
            f for f in session_results["uploaded_files"]
            if f != filename
        ]

        session_results["results"] = [
            r for r in session_results["results"]
            if r["uploaded_filename"] != filename
        ]

        session_results["total_uploaded"] = len(session_results["uploaded_files"])
    return redirect(url_for("results"))


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
        # After a successful upload, pass the current repository list so the page
        # shows the newly added files with the same authoritative count as results.
        repository_files = _load_repository_files()
        return render_template(
            "repository.html",
            form=form,
            uploaded_files=uploaded_files,
            repository_files=repository_files
        )

    # GET request: show the current repository list
    repository_files = _load_repository_files()
    return render_template(
        "repository.html",
        form=form,
        uploaded_files=[],
        repository_files=repository_files
    )


def _load_repository_files():
    base_dir = Path(__file__).resolve().parent.parent.parent
    corpus_promoted = base_dir / "corpus" / "promoted"
    repository_files = {}

    if corpus_promoted.exists():
        for f in sorted(corpus_promoted.iterdir(), key=lambda p: p.name.lower()):
            if not f.is_file():
                continue

            stem = f.stem
            current = repository_files.get(stem)
            if current is None:
                repository_files[stem] = f
            elif current.suffix.lower() == ".txt" and f.suffix.lower() == ".pdf":
                repository_files[stem] = f

    return [
        {
            "filename": file.name,
            "date_added": file.stat().st_mtime,
        }
        for file in sorted(repository_files.values(), key=lambda p: p.name.lower())
    ]


# ============================================================
# Error handlers
# ============================================================
@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", message="An unexpected error occurred. Please try again."), 500


logger.info("main.py finished importing.")

if __name__ == '__main__':
    app.run(debug=DEBUG_MODE)