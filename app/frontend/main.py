import logging
import os
import re
import shutil
import uuid
import json
from pathlib import Path
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms import FileField, SubmitField, MultipleFileField, StringField, PasswordField
from wtforms.validators import InputRequired, Email, EqualTo, ValidationError

from supabase import create_client, Client


from app.services.detector import run_detection
from app.services.review import load_review_report
from app.services.repository import upload_repository
from app.nlp.preprocessing import preprocess_text
from app.utils.document_identity import (
    companion_filename,
    display_filename,
    make_internal_filename,
)
from app.storage.supabase_storage import (
    upload_file,
    delete_file,
)
from dotenv import load_dotenv

load_dotenv()

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


def _audit_log(action, filename=None):
    """
    Print one audit-trail line to the server terminal
    (visible locally and in Render service logs).

    Reuses the existing session values only:
    session["user"] (email) and session["role"] ("admin" or not).
    """

    prefix = "[ADMIN]" if session.get("role") == "admin" else "[USER]"
    email = session.get("user") or "unknown"

    if filename:
        print(f"{prefix} {email} | {action} | {filename}")
    else:
        print(f"{prefix} {email} | {action}")


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
def classify_password_strength(password):
    if (
        len(password) >= 8
        and re.search(r"[a-z]", password)
        and re.search(r"[A-Z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[^A-Za-z0-9]", password)
    ):
        return "strong"

    if (
        len(password) >= 8
        and re.search(r"[A-Za-z]", password)
        and (
            re.search(r"[A-Z]", password)
            or re.search(r"[0-9]", password)
            or re.search(r"[^A-Za-z0-9]", password)
        )
    ):
        return "moderate"

    return "weak"


class WeakPassword(object):
    """
    Rejects passwords classified as weak. Moderate and strong
    passwords are accepted.
    """

    def __call__(self, form, field):
        if classify_password_strength(field.data or "") == "weak":
            raise ValidationError(
                "Password is too weak. Use at least 8 characters and "
                "add numbers or symbols (letters alone are not enough)."
            )


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
            InputRequired(message="Password is required."),
            WeakPassword()
        ]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            InputRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords do not match.")
        ]
    )

    submit = SubmitField("Sign Up")

# ============================================================
# Supabase Settings
# ============================================================
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY environment variable is not set."
    )
if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL environment variable is not set."
    )
if not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_KEY environment variable is not set."
    )
if not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "SUPABASE_SERVICE_KEY environment variable is not set."
    )

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY)
supabase_admin: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)


def create_user_document_record(
    filename,
    source,
    status,
    storage_path=None
):
    """
    Create a record in user_documents for the currently
    logged-in user.
    """

    user_id = session.get("user_id")

    if not user_id:
        raise RuntimeError(
            "Cannot create user document record: "
            "no logged-in user ID in session."
        )

    response = (
        supabase_admin
        .table("user_documents")
        .insert({
            "user_id": user_id,
            "filename": filename,
            "source": source,
            "status": status,
            "storage_path": storage_path
        })
        .execute()
    )

    logger.info(
        "Created user_documents record: user=%s filename=%s source=%s status=%s",
        user_id,
        filename,
        source,
        status
    )

    return response
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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# Routes
# ============================================================
@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template("admin_dashboard.html")

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

                profile_response = (
                    supabase
                    .table("profiles")
                    .select("role")
                    .eq("id", response.user.id)
                    .single()
                    .execute()
                )

                role = profile_response.data["role"]

                print("USER ROLE:", role)

                session['logged_in'] = True
                session['user'] = response.user.email
                session['user_id'] = response.user.id
                session['role'] = role

                flash(
                    f"Welcome to HAUdemicCheck!",
                    "success"
                )

                print("USER ROLE:", role)
                # Redirect based on role
                if role == "admin":
                    return redirect(url_for("admin_dashboard"))

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

# ============================================================
# Admin API Routes
# ============================================================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Get admin panel statistics."""

    base_dir = Path(__file__).resolve().parent.parent.parent

    # ========================================================
    # 1. COUNT USERS
    # ========================================================

    try:
        users_response = (
            supabase_admin
            .table("profiles")
            .select("*")
            .execute()
        )

        users = users_response.data or []

        total_users = len(users)

        active_users = sum(
            1
            for user in users
            if user.get("active", True)
        )

    except Exception:
        logger.exception(
            "ADMIN STATS USER ERROR"
        )

        total_users = 0
        active_users = 0

    # ========================================================
    # 2. REPOSITORY FOLDERS
    #
    # promoted  = actual repository documents
    # review    = documents awaiting review / flagged
    # processed = persistent processed copies
    # ========================================================

    corpus_promoted = (
        base_dir / "corpus" / "promoted"
    )

    corpus_review = (
        base_dir / "corpus" / "review"
    )

    corpus_processed = (
        base_dir / "corpus" / "processed"
    )

    # ========================================================
    # 3. GET PROMOTED REPOSITORY DOCUMENTS
    #
    # ONLY TXT files count.
    #
    # PDFs are ignored because they are companion files.
    # .gitkeep is ignored.
    # ========================================================

    promoted_files = set()

    if corpus_promoted.exists():

        promoted_files = {
            file_path.name
            for file_path in corpus_promoted.iterdir()
            if (
                file_path.is_file()
                and file_path.suffix.lower() == ".txt"
                and file_path.name != ".gitkeep"
            )
        }

    promoted_count = len(promoted_files)

    # ========================================================
    # 4. GET PROCESSED REPOSITORY DOCUMENTS
    #
    # ONLY TXT files count.
    # ========================================================

    processed_files = set()

    if corpus_processed.exists():

        processed_files = {
            file_path.name
            for file_path in corpus_processed.iterdir()
            if (
                file_path.is_file()
                and file_path.suffix.lower() == ".txt"
                and file_path.name != ".gitkeep"
            )
        }

    # ========================================================
    # 5. COUNT PERSISTENT PROCESSED COPIES
    #
    # IMPORTANT:
    #
    # We only count processed files that have a matching
    # document in corpus/promoted.
    #
    # This prevents unrelated/old processed files from
    # inflating the repository health number.
    # ========================================================

    processed_repository_files = (
        promoted_files.intersection(processed_files)
    )

    processed_count = len(
        processed_repository_files
    )

    # ========================================================
    # 6. GET DOCUMENTS WAITING FOR REVIEW
    #
    # corpus/review is now the source of flagged documents.
    #
    # ONLY TXT files count.
    #
    # PDFs and .gitkeep are ignored.
    # ========================================================

    review_files = set()

    if corpus_review.exists():

        review_files = {
            file_path.name
            for file_path in corpus_review.iterdir()
            if (
                file_path.is_file()
                and file_path.suffix.lower() == ".txt"
                and file_path.name != ".gitkeep"
            )
        }

    review_count = len(review_files)

    # ========================================================
    # 7. CALCULATE MISSING PROCESSED COPIES
    #
    # A promoted document is missing a processed copy when
    # its TXT filename does not exist in corpus/processed.
    # ========================================================

    missing_files = (
        promoted_files - processed_files
    )

    missing_count = len(missing_files)

    # ========================================================
    # 8. REPOSITORY HEALTH
    #
    # Healthy when every promoted repository document has
    # a corresponding processed TXT file.
    # ========================================================

    is_synchronized = (
        missing_count == 0
    )

    # ========================================================
    # 9. RETURN DASHBOARD STATISTICS
    # ========================================================

    return jsonify({

        # ------------------------------
        # Users
        # ------------------------------

        "total_users": total_users,
        "active_users": active_users,

        # ------------------------------
        # Repository
        # ------------------------------

        "repository_documents": promoted_count,

        "promoted_copies": promoted_count,

        # ------------------------------
        # Review / Flagged
        # ------------------------------

        "review_documents": review_count,

        "flagged_documents": review_count,

        # ------------------------------
        # Processed copies
        # ------------------------------

        "processed_copies": processed_count,

        # ------------------------------
        # Missing processed copies
        # ------------------------------

        "missing_copies": missing_count,

        # ------------------------------
        # Repository health
        # ------------------------------

        "is_synchronized": is_synchronized
    })



def _load_user_email_map():
    """Map user id to email from profiles, for resolving document uploaders."""
    try:
        response = (
            supabase_admin.table("profiles")
            .select("id, email")
            .execute()
        )
    except Exception:
        logger.exception("Could not load user email metadata")
        return {}

    return {
        str(record.get("id")): record.get("email")
        for record in (response.data or [])
        if record.get("id") and record.get("email")
    }


def _repository_document_indexes():
    """Index optional database metadata without hiding local repository files."""
    try:
        response = (
            supabase_admin.table("user_documents")
            .select("id, filename, storage_path, user_id")
            .execute()
        )
    except Exception:
        logger.exception("Could not load repository document metadata")
        return {}, {}

    by_storage_name = {}
    legacy_by_filename = {}
    for record in response.data or []:
        storage_path = record.get("storage_path")
        filename = record.get("filename")
        if storage_path and str(storage_path).lstrip("/").startswith("promoted/"):
            by_storage_name[Path(storage_path).name] = record
        elif not storage_path and filename:
            legacy_by_filename[filename] = record
            legacy_by_filename[companion_filename(filename, ".txt")] = record

    return by_storage_name, legacy_by_filename


def _repository_file_payload(file_path, by_storage_name, legacy_by_filename, user_emails):
    """Build a display/API record for one local promoted TXT file."""
    document = (
        by_storage_name.get(file_path.name)
        or legacy_by_filename.get(file_path.name)
    )
    stat = file_path.stat()

    added_by = "SYSTEM"
    if document and document.get("user_id"):
        added_by = user_emails.get(str(document["user_id"])) or "SYSTEM"

    return {
        "document_id": document.get("id") if document else None,
        # A local-only legacy file has no database identity. Its immutable
        # repository filename is used only by the legacy delete fallback.
        "legacy_filename": None if document else file_path.name,
        "filename": (
            document.get("filename")
            if document else display_filename(file_path.name)
        ),
        "added_by": added_by,
        "date_added": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "size": stat.st_size,
    }


@app.route('/api/admin/repository', methods=['GET'])
@admin_required
def get_repository_files():
    """List local repository files and enrich them with database metadata."""

    base_dir = Path(__file__).resolve().parent.parent.parent
    corpus_promoted = base_dir / "corpus" / "promoted"
    by_storage_name, legacy_by_filename = _repository_document_indexes()
    user_emails = _load_user_email_map()

    files = []
    if corpus_promoted.exists():
        for file_path in sorted(corpus_promoted.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() == ".txt":
                files.append(_repository_file_payload(
                    file_path,
                    by_storage_name,
                    legacy_by_filename,
                    user_emails,
                ))

    return jsonify(files)

@app.route('/api/admin/repository/<document_ref>', methods=['DELETE'])
@admin_required
def delete_repository_file(document_ref):
    """
    Permanently delete a repository document.

    The deletion is synchronized across:

        1. Local corpus/promoted
        2. Local corpus/processed
        3. Supabase Storage
        4. user_documents database records

    The user_documents row ID is the repository document identity.
    PDF files are treated as companion files and are removed when present.

    IMPORTANT:
    The database is queried BEFORE deleting anything so that we can
    retrieve the actual storage_path instead of relying only on guessed
    Supabase paths.
    """

    # ----------------------------------------------------------
    # 1. Find the exact database row before touching any files.
    # ----------------------------------------------------------

    document = None
    is_document_id = False
    try:
        uuid.UUID(str(document_ref))
    except (ValueError, TypeError, AttributeError):
        pass
    else:
        is_document_id = True
        try:
            document_response = (
                supabase_admin
                .table("user_documents")
                .select("*")
                .eq("id", document_ref)
                .execute()
            )
            records = document_response.data or []
            document = records[0] if records else None
        except Exception:
            logger.exception("Could not load repository document %s", document_ref)
            return jsonify({"error": "Repository document lookup failed."}), 500

    if not document:
        # Only local-only legacy files use this route fallback. New files
        # always have a row ID and must never be identified by display name.
        if is_document_id:
            return jsonify({"error": "Repository document record not found."}), 404
        legacy_filename = Path(document_ref).name
        document = {
            "id": None,
            "filename": display_filename(legacy_filename),
            "storage_path": None,
        }
    filename = document.get("filename", "document")
    internal_name = (
        Path(document["storage_path"]).name
        if document.get("storage_path")
        else filename
    )

    # Repository documents are TXT documents.
    # If the frontend happens to send a PDF filename, normalize it
    # to the corresponding TXT document.
    path = Path(internal_name)

    if path.suffix.lower() == ".pdf":
        txt_name = path.with_suffix(".txt").name
        pdf_name = path.name
    elif path.suffix.lower() == ".txt":
        txt_name = path.name
        pdf_name = path.with_suffix(".pdf").name
    else:
        txt_name = path.with_suffix(".txt").name
        pdf_name = path.with_suffix(".pdf").name

    logger.info(
        "ADMIN REPOSITORY DELETE START: filename=%s txt=%s pdf=%s",
        filename,
        txt_name,
        pdf_name
    )

    try:

        # ------------------------------------------------------
        # 2. Locate project folders
        # ------------------------------------------------------

        base_dir = Path(__file__).resolve().parent.parent.parent

        promoted_folder = (
            base_dir / "corpus" / "promoted"
        )

        processed_folder = (
            base_dir / "corpus" / "processed"
        )

        # ------------------------------------------------------
        # 3. FIND DATABASE RECORDS FIRST
        # ------------------------------------------------------
        #
        # Do this BEFORE deleting local files.
        #
        # The exact row above is authoritative.  Do not locate rows by
        # display filename: multiple documents may share it.
        # ------------------------------------------------------

        db_records = [document]

        logger.info(
            "Repository delete database records found: %s",
            db_records
        )

        # ------------------------------------------------------
        # 4. COLLECT EXACT STORAGE PATHS FROM DATABASE
        # ------------------------------------------------------
        #
        # This is important.
        #
        # Do not depend only on:
        #
        #     promoted/foo.txt
        #
        # because the database may contain the actual storage_path
        # used when the file was uploaded.
        # ------------------------------------------------------

        storage_paths = set()

        for record in db_records:

            storage_path = record.get("storage_path")

            if storage_path:
                storage_paths.add(
                    str(storage_path).lstrip("/")
                )

        # ------------------------------------------------------
        # 5. ALSO ADD THE KNOWN REPOSITORY PATHS
        # ------------------------------------------------------
        #
        # These cover repository files created before storage_path
        # was consistently saved in user_documents.
        # ------------------------------------------------------

        storage_paths.update({
            f"promoted/{txt_name}",
            f"promoted/{pdf_name}",
            f"processed/{txt_name}"
        })

        logger.info(
            "Repository storage paths scheduled for deletion: %s",
            sorted(storage_paths)
        )

        # ------------------------------------------------------
        # 6. DELETE LOCAL PROMOTED FILES
        # ------------------------------------------------------

        local_paths = [
            promoted_folder / txt_name,
            promoted_folder / pdf_name,
            processed_folder / txt_name
        ]

        local_deleted = []

        for local_file in local_paths:

            if local_file.exists() and local_file.is_file():

                local_file.unlink()

                local_deleted.append(
                    str(local_file)
                )

                logger.info(
                    "Deleted local repository file: %s",
                    local_file
                )

        # ------------------------------------------------------
        # 7. DELETE SUPABASE STORAGE FILES
        # ------------------------------------------------------
        #
        # Every path is attempted.
        #
        # A missing companion file should NOT prevent deletion of
        # the database record.
        #
        # However, if an actual deletion operation throws an error,
        # we stop and report the error instead of claiming success.
        # ------------------------------------------------------

        storage_deleted = []

        storage_errors = []

        for storage_path in sorted(storage_paths):

            try:

                delete_file(storage_path)

                storage_deleted.append(
                    storage_path
                )

                logger.info(
                    "Deleted Supabase Storage object: %s",
                    storage_path
                )

            except Exception as e:

                error_text = str(e)

                logger.warning(
                    "Could not delete Supabase Storage object %s: %s",
                    storage_path,
                    error_text
                )

                storage_errors.append({
                    "path": storage_path,
                    "error": error_text
                })

        # ------------------------------------------------------
        # 8. DO NOT DELETE DATABASE RECORDS IF STORAGE FAILED
        # ------------------------------------------------------
        #
        # This prevents the database from saying the document is
        # gone while the actual Storage object still exists.
        #
        # Local files may already have been removed, but the
        # database remains intact so the operation can be retried.
        # ------------------------------------------------------

        if storage_errors:

            logger.error(
                "Repository deletion stopped because Storage deletion "
                "failed: %s",
                storage_errors
            )

            return jsonify({
                "error": (
                    "Repository document was not completely deleted. "
                    "One or more Supabase Storage objects could not "
                    "be removed."
                ),
                "storage_errors": storage_errors,
                "local_deleted": local_deleted
            }), 500

        # ------------------------------------------------------
        # 9. DELETE DATABASE RECORDS
        # ------------------------------------------------------
        #
        # Delete by exact database ID when possible.
        #
        # This is safer than:
        #
        #     .eq("filename", filename)
        #
        # because filenames are not guaranteed to be unique.
        # ------------------------------------------------------

        deleted_records = []

        for record in db_records:

            record_id = record.get("id")

            if not record_id:
                continue

            delete_response = (
                supabase_admin
                .table("user_documents")
                .delete()
                .eq("id", record_id)
                .execute()
            )

            if delete_response.data:

                deleted_records.extend(
                    delete_response.data
                )

                logger.info(
                    "Deleted user_documents record: id=%s",
                    record_id
                )

        # ------------------------------------------------------
        # 10. SUCCESS
        # ------------------------------------------------------

        logger.info(
            "ADMIN REPOSITORY DELETE COMPLETE: "
            "filename=%s local=%s storage=%s database=%s",
            filename,
            len(local_deleted),
            len(storage_deleted),
            len(deleted_records)
        )

        _audit_log("DELETE", filename)

        return jsonify({
            "success": True,
            "filename": filename,
            "message": (
                f"Repository document '{filename}' "
                "was permanently deleted."
            ),
            "local_deleted": local_deleted,
            "storage_deleted": storage_deleted,
            "database_deleted": deleted_records
        })

    except Exception as e:

        logger.exception(
            "ADMIN REPOSITORY DELETE ERROR: %s",
            filename
        )

        return jsonify({
            "error": str(e),
            "filename": filename
        }), 500


@app.route("/api/admin/flagged", methods=["GET"])
@login_required
def admin_flagged_documents():

    if session.get("role") != "admin":
        return jsonify({
            "error": "Admin privileges required."
        }), 403

    try:

        base_dir = Path(__file__).resolve().parent.parent.parent
        flagged_folder = base_dir / "corpus" / "review"

        if not flagged_folder.exists():
            return jsonify([])

        files = []
        records_response = (
            supabase_admin.table("user_documents")
            .select("id, filename, storage_path, user_id")
            .eq("source", "plagiarism_check")
            .execute()
        )
        user_emails = _load_user_email_map()
        records_by_storage_name = {
            Path(record["storage_path"]).name: record
            for record in (records_response.data or [])
            if record.get("storage_path")
            and str(record["storage_path"]).startswith("review/")
        }
        legacy_records_by_filename = {
            record.get("filename"): record
            for record in (records_response.data or [])
            if not record.get("storage_path")
        }

        for file_path in flagged_folder.iterdir():

            if not file_path.is_file():
                continue

            if file_path.suffix.lower() != ".txt":
                continue

            if file_path.name == ".gitkeep":
                continue

            document = (
                records_by_storage_name.get(file_path.name)
                or legacy_records_by_filename.get(file_path.name)
            )
            if not document:
                continue

            files.append({
                "document_id": document.get("id"),
                "filename": document.get("filename", display_filename(file_path.name)),
                "added_by": (
                    user_emails.get(str(document.get("user_id")))
                    if document.get("user_id")
                    else None
                ) or "SYSTEM",
                "date_added": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat()
            })

        files.sort(
            key=lambda item: item["date_added"],
            reverse=True
        )

        return jsonify(files)

    except Exception as e:

        logger.exception(
            "Failed to load flagged documents"
        )

        return jsonify({
            "error": str(e)
        }), 500

@app.route("/api/admin/flagged/search", methods=["GET"])
@login_required
def search_admin_flagged_documents():

    if session.get("role") != "admin":
        return jsonify({
            "error": "Admin privileges required."
        }), 403

    try:

        query = request.args.get("q", "").strip().lower()

        base_dir = Path(__file__).resolve().parent.parent.parent
        flagged_folder = base_dir / "corpus" / "review"

        if not flagged_folder.exists():
            return jsonify([])

        files = []
        records_response = (
            supabase_admin.table("user_documents")
            .select("id, filename, storage_path, user_id")
            .eq("source", "plagiarism_check")
            .execute()
        )
        user_emails = _load_user_email_map()
        records_by_storage_name = {
            Path(record["storage_path"]).name: record
            for record in (records_response.data or [])
            if record.get("storage_path")
            and str(record["storage_path"]).startswith("review/")
        }
        legacy_records_by_filename = {
            record.get("filename"): record
            for record in (records_response.data or [])
            if not record.get("storage_path")
        }

        for file_path in flagged_folder.iterdir():

            if not file_path.is_file():
                continue

            if file_path.suffix.lower() != ".txt":
                continue

            if file_path.name == ".gitkeep":
                continue

            document = (
                records_by_storage_name.get(file_path.name)
                or legacy_records_by_filename.get(file_path.name)
            )
            if not document:
                continue

            display_name = document.get("filename", display_filename(file_path.name))
            if query and query not in display_name.lower():
                continue

            files.append({
                "document_id": document.get("id"),
                "filename": display_name,
                "added_by": (
                    user_emails.get(str(document.get("user_id")))
                    if document.get("user_id")
                    else None
                ) or "SYSTEM",
                "date_added": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat()
            })

        files.sort(
            key=lambda item: item["date_added"],
            reverse=True
        )

        return jsonify(files)

    except Exception as e:

        logger.exception(
            "Failed to search flagged documents"
        )

        return jsonify({
            "error": str(e)
        }), 500

@app.route("/api/admin/flagged/<document_id>", methods=["DELETE"])
@login_required
def delete_admin_flagged_document(document_id):

    if session.get("role") != "admin":
        return jsonify({
            "error": "Admin privileges required."
        }), 403

    try:

        base_dir = Path(__file__).resolve().parent.parent.parent

        flagged_folder = base_dir / "corpus" / "review"

        if not flagged_folder.exists():
            return jsonify({
                "error": "Flagged directory does not exist."
            }), 404

        document_response = (
            supabase_admin
            .table("user_documents")
            .select("id, filename, source, storage_path")
            .eq("id", document_id)
            .eq("source", "plagiarism_check")
            .single()
            .execute()
        )
        document = document_response.data
        if not document:
            return jsonify({"error": "Flagged document record not found."}), 404

        filename = document.get("filename", "document")
        internal_name = (
            Path(document["storage_path"]).name
            if document.get("storage_path")
            else filename
        )

        # --------------------------------------------------
        # Determine TXT / PDF pair
        # --------------------------------------------------

        path = Path(internal_name)

        if path.suffix.lower() == ".pdf":

            pdf_name = path.name
            txt_name = path.with_suffix(".txt").name

        elif path.suffix.lower() == ".txt":

            txt_name = path.name
            pdf_name = path.with_suffix(".pdf").name

        else:

            txt_name = path.with_suffix(".txt").name
            pdf_name = path.with_suffix(".pdf").name

        # --------------------------------------------------
        # Local paths
        # --------------------------------------------------

        local_paths = [
            flagged_folder / txt_name,
            flagged_folder / pdf_name,
        ]

        # --------------------------------------------------
        # Supabase paths
        # --------------------------------------------------

        storage_paths = [
            f"review/{txt_name}",
            f"review/{pdf_name}",
        ]

        deleted_any = False

        # --------------------------------------------------
        # Delete local files
        # --------------------------------------------------

        for local_file in local_paths:

            if local_file.exists() and local_file.is_file():

                local_file.unlink()

                deleted_any = True

                logger.info(
                    "Admin deleted flagged local file: %s",
                    local_file
                )

        # --------------------------------------------------
        # Delete Supabase Storage copies
        # --------------------------------------------------

        for storage_path in storage_paths:

            try:

                delete_file(storage_path)

                logger.info(
                    "Admin deleted flagged Supabase object: %s",
                    storage_path
                )

            except Exception as e:

                logger.exception(
                    "Failed deleting flagged Supabase object: %s",
                    storage_path
                )

                raise e

        # --------------------------------------------------
        # Delete the corresponding database record
        # --------------------------------------------------

        supabase_admin \
            .table("user_documents") \
            .delete() \
            .eq("id", document_id) \
            .eq("source", "plagiarism_check") \
            .execute()

        logger.info(
            "Admin deleted flagged user_documents record: id=%s",
            document_id
        )

        if not deleted_any:

            return jsonify({
                "error": "Flagged document not found."
            }), 404

        logger.info(
            "Admin flagged document deletion completed: %s",
            filename
        )

        _audit_log("DELETE", filename)

        return jsonify({
            "success": True,
            "message": f"Flagged document '{filename}' deleted successfully."
        })

    except Exception as e:

        logger.exception(
            "ADMIN FLAGGED DOCUMENT DELETE ERROR: %s",
            filename
        )

        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/my-documents/<document_id>', methods=['DELETE'])
@login_required
def delete_my_document(document_id):
    """Delete one of the current user's documents by its database row ID."""

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "error": "User session not found."
        }), 401

    try:

        response = (
            supabase_admin
            .table("user_documents")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", document_id)
            .single()
            .execute()
        )

        document = response.data

        if not document:
            return jsonify({
                "error": "Document record not found."
            }), 404

        source = document.get("source")
        filename = document.get("filename", "document")
        storage_path = document.get("storage_path")

        logger.info(
            "User deleting document: user=%s id=%s filename=%s source=%s",
            user_id,
            document_id,
            filename,
            source
        )

        # The stored path is authoritative for new records.  A filename
        # fallback preserves deletion of legacy rows that predate it.
        internal_name = Path(storage_path).name if storage_path else filename
        txt_name = companion_filename(internal_name, ".txt")
        pdf_name = companion_filename(internal_name, ".pdf")

        # --------------------------------------------------
        # 3. Determine local + Supabase locations
        # --------------------------------------------------

        base_dir = Path(__file__).resolve().parent.parent.parent

        promoted_folder = base_dir / "corpus" / "promoted"
        processed_folder = base_dir / "corpus" / "processed"
        review_folder = base_dir / "corpus" / "review"
        upload_folder = Path(app.config["UPLOAD_FOLDER"])

        txt_upload_folder = TXT_UPLOAD_FOLDER

        # --------------------------------------------------
        if source not in {"repository", "plagiarism_check"}:

            return jsonify({
                "error": f"Unsupported document source: {source}"
            }), 400

        local_paths = [
            upload_folder / pdf_name,
            upload_folder / txt_name,
            txt_upload_folder / txt_name,
            review_folder / txt_name,
            review_folder / pdf_name,
            promoted_folder / txt_name,
            promoted_folder / pdf_name,
            processed_folder / txt_name,
        ]
        storage_paths = {
            f"review/{txt_name}",
            f"review/{pdf_name}",
            f"promoted/{txt_name}",
            f"promoted/{pdf_name}",
            f"processed/{txt_name}",
        }

        for local_file in local_paths:

            if local_file.exists() and local_file.is_file():

                local_file.unlink()

                logger.info(
                    "Deleted local document copy: %s",
                    local_file
                )

        # --------------------------------------------------
        # 5. Delete Supabase Storage copies
        # --------------------------------------------------

        for storage_path in storage_paths:

            try:

                delete_file(storage_path)

                logger.info(
                    "Deleted Supabase Storage object: %s",
                    storage_path
                )

            except Exception as e:

                logger.exception(
                    "Failed to delete Supabase object %s",
                    storage_path
                )

                raise e

        delete_response = (
            supabase_admin
            .table("user_documents")
            .delete()
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )

        if not delete_response.data:
            return jsonify({
                "error": "Document database record could not be deleted."
            }), 500

        logger.info(
            "Deleted user_documents record: user=%s id=%s filename=%s",
            user_id,
            document_id,
            filename
        )

        # --------------------------------------------------
        # 7. Success
        # --------------------------------------------------

        _audit_log("DELETE", filename)

        return jsonify({
            "success": True,
            "message": f"Document '{filename}' deleted successfully."
        })

    except Exception as e:

        logger.exception(
            "DELETE MY DOCUMENT ERROR: user=%s id=%s",
            user_id,
            document_id
        )

        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/admin/plagiarism/<document_id>', methods=['DELETE'])
@admin_required
def delete_plagiarism_document(document_id):
    """
    Delete a plagiarism-uploaded document using its database row ID.

    Deletes:
        1. The corresponding Supabase Storage object
        2. The corresponding user_documents database row

    Does NOT identify the document by filename.
    """

    try:
        # --------------------------------------------------
        # 1. Get the exact database row by ID
        # --------------------------------------------------

        response = (
            supabase_admin
            .table("user_documents")
            .select("*")
            .eq("id", document_id)
            .eq("source", "plagiarism_check")
            .single()
            .execute()
        )

        document = response.data

        if not document:
            return jsonify({
                "error": "Plagiarism document record not found."
            }), 404

        logger.info(
            "Admin deleting plagiarism document: id=%s filename=%s",
            document_id,
            document.get("filename")
        )

        # --------------------------------------------------
        # 2. Get the exact Storage path from the row
        # --------------------------------------------------

        storage_path = document.get("storage_path")

        # --------------------------------------------------
        # 3. Delete Storage object if one exists
        # --------------------------------------------------

        if storage_path:
            try:
                delete_file(storage_path)

                logger.info(
                    "Deleted plagiarism document from Supabase Storage: %s",
                    storage_path
                )

            except Exception as e:
                logger.exception(
                    "Failed to delete plagiarism Storage object: %s",
                    storage_path
                )

                return jsonify({
                    "error": (
                        "Storage deletion failed. "
                        "Database record was not deleted."
                    ),
                    "details": str(e)
                }), 500

        # --------------------------------------------------
        # 4. Delete EXACT database row
        # --------------------------------------------------

        delete_response = (
            supabase_admin
            .table("user_documents")
            .delete()
            .eq("id", document_id)
            .eq("source", "plagiarism_check")
            .execute()
        )

        if not delete_response.data:
            return jsonify({
                "error": "Database record could not be deleted."
            }), 500

        logger.info(
            "Deleted plagiarism user_documents row: id=%s",
            document_id
        )

        # --------------------------------------------------
        # 5. Success
        # --------------------------------------------------

        _audit_log(
            "DELETE",
            document.get("filename", "document")
        )

        return jsonify({
            "success": True,
            "message": "Plagiarism document deleted successfully.",
            "document_id": document_id
        })

    except Exception as e:

        logger.exception(
            "DELETE PLAGIARISM DOCUMENT ERROR: %s",
            document_id
        )

        return jsonify({
            "error": str(e)
        }), 500


@app.route('/api/admin/repository/search', methods=['GET'])
@admin_required
def search_repository():
    """Search repository documents by filename."""

    query = request.args.get('q', '').strip().lower()

    base_dir = Path(__file__).resolve().parent.parent.parent
    corpus_promoted = base_dir / "corpus" / "promoted"

    files = []
    by_storage_name, legacy_by_filename = _repository_document_indexes()
    user_emails = _load_user_email_map()

    if corpus_promoted.exists():
        for file_path in sorted(corpus_promoted.iterdir()):
            if not file_path.is_file() or file_path.suffix.lower() != ".txt":
                continue
            payload = _repository_file_payload(
                file_path,
                by_storage_name,
                legacy_by_filename,
                user_emails,
            )
            if query in payload["filename"].lower():
                files.append(payload)

    return jsonify(files)

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    """Get list of all users."""
    try:
        users_response = (
            supabase_admin
            .table("profiles")
            .select("id,email,role")
            .execute()
        )
        users = users_response.data or []

        return jsonify(users)

    except Exception as e:
        print("GET USERS ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/admin/users', methods=['POST'])
@admin_required
def create_admin_user():
    try:
        data = request.get_json()

        email = data.get("email", "").strip()
        password = data.get("password", "")
        role = data.get("role", "").strip().lower()

        if not email:
            return jsonify({"error": "Email is required"}), 400

        if not password:
            return jsonify({"error": "Password is required"}), 400

        if role not in ["admin", "instructor"]:
            return jsonify({
                "error": "Role must be admin or instructor"
            }), 400

        if len(password) < 8:
            return jsonify({
                "error": "Password must be at least 8 characters"
            }), 400

        if not any(c.isupper() for c in password):
            return jsonify({
                "error": "Password must contain an uppercase letter"
            }), 400

        if not any(c.islower() for c in password):
            return jsonify({
                "error": "Password must contain a lowercase letter"
            }), 400

        if not any(c.isdigit() for c in password):
            return jsonify({
                "error": "Password must contain a number"
            }), 400

        # Create authentication account
        response = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })

        if not response.user:
            return jsonify({
                "error": "Failed to create authentication account"
            }), 500

        user_id = response.user.id

        # Create profile
        supabase_admin.table("profiles").insert({
            "id": user_id,
            "email": email,
            "role": role
        }).execute()

        return jsonify({
            "success": True,
            "message": "User created successfully",
            "user": {
                "id": user_id,
                "email": email,
                "role": role
            }
        }), 201

    except Exception as e:
        print("CREATE USER ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/admin/system-status', methods=['GET'])
@admin_required
def get_system_status():
    """Get system health status."""

    base_dir = Path(__file__).resolve().parent.parent.parent

    status = {
        "authentication": "operational",
        "upload": "operational",
        "preprocessing": "operational",
        "similarity_analysis": "operational",
        "repository": "operational",
        "persistent_processing": "operational"
    }

    # Check if key folders exist
    try:
        if not (base_dir / "corpus" / "promoted").exists():
            status["repository"] = "warning"

        if not (base_dir / "corpus" / "processed").exists():
            status["persistent_processing"] = "warning"

    except Exception as e:
        print("SYSTEM STATUS ERROR:", repr(e))

    return jsonify(status)

@app.route('/api/admin/activity', methods=['GET'])
@admin_required
def get_recent_activity():
    """Get recent system activity."""

    activity = []

    activity.append({
        "type": "system_status",
        "description": "Admin panel initialized",
        "timestamp": datetime.now().isoformat(),
        "updated_by": "system",
        "icon": "✓"
    })

    return jsonify(
        sorted(
            activity,
            key=lambda x: x["timestamp"],
            reverse=True
        )[:10]
    )

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user from Supabase Authentication and profiles."""

    try:
        # Prevent the admin from deleting their own account
        if user_id == session.get('user_id'):
            return jsonify({
                "error": "You cannot delete your own account."
            }), 400

        # Delete profile
        supabase_admin \
            .table("profiles") \
            .delete() \
            .eq("id", user_id) \
            .execute()

        # Delete authentication account
        supabase_admin.auth.admin.delete_user(user_id)

        return jsonify({
            "success": True,
            "message": "User deleted successfully."
        })

    except Exception as e:
        print("DELETE USER ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/admin/users/<user_id>', methods=['PATCH'])
@admin_required
def update_user(user_id):
    """Update a user's email or role."""

    try:
        data = request.get_json()

        email = data.get("email", "").strip()
        role = data.get("role", "").strip().lower()

        if not email:
            return jsonify({
                "error": "Email is required."
            }), 400

        if role not in ["admin", "instructor"]:
            return jsonify({
                "error": "Role must be admin or instructor."
            }), 400

        # Update authentication email
        supabase_admin.auth.admin.update_user_by_id(
            user_id,
            {
                "email": email
            }
        )

        # Update profile
        supabase_admin \
            .table("profiles") \
            .update({
                "email": email,
                "role": role
            }) \
            .eq("id", user_id) \
            .execute()

        return jsonify({
            "success": True,
            "message": "User updated successfully.",
            "user": {
                "id": user_id,
                "email": email,
                "role": role
            }
        })

    except Exception as e:
        print("UPDATE USER ERROR:", repr(e))

        return jsonify({
            "error": str(e)
        }), 500

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

        # Map each internal TXT companion name to the original
        # uploaded filename so user_documents can show the real
        # .pdf display name without touching internal identities.
        upload_display_names = {}

        for file in form.files.data:
            original_filename = secure_filename(file.filename)
            if not original_filename:
                continue
            filename = make_internal_filename(original_filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            upload_display_names[
                companion_filename(filename, ".txt")
            ] = original_filename
            logger.info(
                "Saved upload: display=%s internal=%s path=%s",
                original_filename,
                filename,
                save_path,
            )

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


        # --------------------------------------------------
        # Record plagiarism-uploaded documents
        # --------------------------------------------------

        for result in results["results"]:

            internal_filename = result["uploaded_filename"]

            # Display the original uploaded filename (e.g.
            # research_paper.pdf). The internal TXT name is only a
            # fallback for results without a matching upload entry.
            filename = upload_display_names.get(
                internal_filename,
                display_filename(internal_filename),
            )

            # A document is flagged when the detector found
            # at least one flagged similarity pair.
            if len(result["flagged"]) > 0:
                status = "flagged"
            else:
                status = "original"

            try:
                create_user_document_record(
                    filename=filename,
                    source="plagiarism_check",
                    status=status,
                    storage_path=(
                        f"review/{internal_filename}"
                        if status == "flagged"
                        else f"promoted/{internal_filename}"
                    ),
                )

            except Exception as e:
                logger.exception(
                    "Failed to create user_documents record for %s",
                    filename
                )

                print("USER DOCUMENT INSERT ERROR:", repr(e))

                return render_template(
                    "error.html",
                    message=(
                        f"Document was analyzed, but upload record failed: {e}"
                    )
                ), 500

            # Keep routing on the internal name, but never expose it as
            # the document name in the results UI.
            result["display_filename"] = filename

            _audit_log("PLAGIARISM CHECK", filename)


        results["threshold"] = threshold
        RESULTS_STORE[get_session_id()] = results

        counts = _results_page_counts(results)

        return render_template(
            "results.html",
            uploaded_files=results["uploaded_files"],
            total_uploaded=counts["total_uploaded"],
            compared_against=counts["compared_against"],
            flagged_files=counts["flagged_files"],
            total_repository=counts["total_repository"],
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
    session_results = RESULTS_STORE.get(get_session_id(), {})
    threshold = session_results.get("threshold")
    return render_template(
        "review.html",
        review=report,
        threshold=threshold,
    )

@app.route("/review/<filename>/dismiss", methods=["POST"])
@login_required
def dismiss_flag(filename):
    """
    Instructor determined the document is original.

    Local:
        review -> promoted
        create processed copy

    Supabase:
        review -> promoted
        create processed copy
    """

    txt_source = REVIEW_FOLDER / filename
    txt_destination = PROMOTED_FOLDER / filename

    pdf_name = Path(filename).stem + ".pdf"

    pdf_source = REVIEW_FOLDER / pdf_name
    pdf_destination = PROMOTED_FOLDER / pdf_name

    processed_file = PROCESSED_FOLDER / filename

    moved_successfully = False

    try:

        # ==================================================
        # 1. Move TXT locally: review -> promoted
        # ==================================================

        if not txt_source.exists():
            raise FileNotFoundError(
                f"Review TXT not found: {txt_source}"
            )

        shutil.move(
            str(txt_source),
            str(txt_destination)
        )

        print(f"Promoted TXT locally: {filename}")

        # ==================================================
        # 2. Generate processed repository copy locally
        # ==================================================

        PROCESSED_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

        processed_text = preprocess_text(
            txt_destination
        )

        processed_file.write_text(
            processed_text,
            encoding="utf-8"
        )

        print(f"Processed TXT locally: {filename}")

        # ==================================================
        # 3. Move PDF locally: review -> promoted
        # ==================================================

        if pdf_source.exists():

            shutil.move(
                str(pdf_source),
                str(pdf_destination)
            )

            print(f"Promoted PDF locally: {pdf_name}")

        # ==================================================
        # 4. Upload promoted TXT to Supabase
        # ==================================================

        upload_file(
            txt_destination,
            f"promoted/{filename}",
            overwrite=True
        )

        print(
            f"Uploaded promoted TXT to Supabase: {filename}"
        )

        # ==================================================
        # 5. Upload processed TXT to Supabase
        # ==================================================

        upload_file(
            processed_file,
            f"processed/{filename}",
            overwrite=True
        )

        print(
            f"Uploaded processed TXT to Supabase: {filename}"
        )

        # ==================================================
        # 6. Upload promoted PDF to Supabase
        # ==================================================

        if pdf_destination.exists():

            pdf_size = pdf_destination.stat().st_size

            if pdf_size <= 50 * 1024 * 1024:

                upload_file(
                    pdf_destination,
                    f"promoted/{pdf_name}",
                    overwrite=True
                )

                print(
                    f"Uploaded promoted PDF to Supabase: "
                    f"{pdf_name}"
                )

            else:
                print(
                    f"[WARNING] {pdf_name} exceeds the "
                    f"Supabase Free 50 MB limit. "
                    f"PDF was not uploaded to Supabase."
                )

        # ==================================================
        # 7. Remove old review copies from Supabase
        # ==================================================

        delete_file(
            f"review/{filename}"
        )

        print(
            f"Deleted review TXT from Supabase: {filename}"
        )

        # --------------------------------------------------
        # Delete review PDF if it existed
        # --------------------------------------------------

        if pdf_destination.exists():

            delete_file(
                f"review/{pdf_name}"
            )

            print(
                f"Deleted review PDF from Supabase: "
                f"{pdf_name}"
            )

        moved_successfully = True

        flash(
            "Document promoted to repository.",
            "success"
        )

    except Exception as e:

        logger.exception(
            "Dismiss Flag failed for %s",
            filename
        )

        flash(
            f"Unable to promote the document: {e}",
            "danger"
        )

    # ======================================================
    # Remove promoted document from current session results
    # ======================================================

    if moved_successfully:

        # Keep the row's authoritative object path in sync with the move.
        # `filename` is only a display value, so the exact old Storage path
        # identifies this document even when display filenames are duplicated.
        supabase_admin \
            .table("user_documents") \
            .update({
                "storage_path": f"promoted/{filename}",
                "status": "original",
            }) \
            .eq("storage_path", f"review/{filename}") \
            .eq("source", "plagiarism_check") \
            .execute()

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


def _results_page_counts(results_data):
    """
    Derive the Results-page counts from the stored detection results.

    `total_repository` from run_detection() is counted AFTER promotion,
    and only non-flagged uploads are ever appended to the repository
    (flagged ones go to review), so it is the repository size including
    this batch's successful additions. The count the uploads were
    compared against is that value minus this batch's promotions.
    """
    results = results_data.get("results", [])
    flagged_files = sum(1 for r in results if r.get("flagged"))
    promoted_files = sum(1 for r in results if not r.get("flagged"))
    total_repository = results_data.get("total_repository", 0)

    return {
        "total_uploaded": results_data.get(
            "total_uploaded",
            len(results),
        ),
        "compared_against": total_repository - promoted_files,
        "flagged_files": flagged_files,
        "total_repository": total_repository,
    }


@app.route("/results")
@login_required
def results():
    last_results = RESULTS_STORE.get(get_session_id())
    if last_results is None:
        return redirect(url_for("home"))

    counts = _results_page_counts(last_results)

    return render_template(
        "results.html",
        uploaded_files=last_results["uploaded_files"],
        total_uploaded=counts["total_uploaded"],
        compared_against=counts["compared_against"],
        flagged_files=counts["flagged_files"],
        total_repository=counts["total_repository"],
        results=last_results["results"]
    )


@app.route("/repository", methods=["GET", "POST"])
@login_required
def repository():
    form = RepositoryUploadForm()

    if form.validate_on_submit():

        for file in form.files.data:
            original_filename = secure_filename(file.filename)
            if not original_filename:
                continue
            filename = make_internal_filename(original_filename)

            save_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            file.save(save_path)

            logger.info(
                "Repository upload: display=%s internal=%s",
                original_filename,
                filename,
            )

        try:
            uploaded_files = upload_repository()

        except Exception:
            logger.exception(
                "Repository upload failed"
            )

            return render_template(
                "error.html",
                message=(
                    "The documents could not be added "
                    "to the repository. Please try again."
                )
            ), 500

        # --------------------------------------------------
        # Record repository uploads in user_documents
        # --------------------------------------------------

        uploaded_documents = []

        for internal_pdf_name in uploaded_files:

            filename = display_filename(internal_pdf_name)
            internal_txt_name = companion_filename(
                internal_pdf_name,
                ".txt"
            )
            storage_path = f"promoted/{internal_txt_name}"

            try:
                insert_response = create_user_document_record(
                    filename=filename,
                    source="repository",
                    status="original",
                    storage_path=storage_path,
                )

                created_data = insert_response.data or []
                if isinstance(created_data, list):
                    document = created_data[0] if created_data else None
                else:
                    document = created_data

                # Supabase configurations that do not return inserted rows
                # still have one unambiguous lookup: the UUID-backed path.
                if not document or not document.get("id"):
                    document_response = (
                        supabase_admin
                        .table("user_documents")
                        .select("id, filename, storage_path")
                        .eq("storage_path", storage_path)
                        .single()
                        .execute()
                    )
                    document = document_response.data

                uploaded_documents.append({
                    "id": document.get("id"),
                    "filename": document.get("filename", filename),
                })

                _audit_log("REPOSITORY UPLOAD", filename)

            except Exception as e:
                logger.exception(
                    "Failed to create user_documents "
                    "record for repository file %s",
                    filename
                )

                print(
                    "REPOSITORY DOCUMENT RECORD ERROR:",
                    repr(e)
                )

                return render_template(
                    "error.html",
                    message=(
                        "The document was added to the repository, "
                        "but we could not save its upload record."
                    )
                ), 500

        # Use Post/Redirect/Get so Ctrl+R performs a read-only GET.  The
        # success card describes the rows just persisted above; it does not
        # manufacture filenames or identities during rendering.
        session["repository_upload_success"] = uploaded_documents
        return redirect(url_for("repository"))

    # ------------------------------------------------------
    # GET request
    # ------------------------------------------------------

    user_documents = _load_user_documents()
    uploaded_documents = session.pop("repository_upload_success", [])

    return render_template(
        "repository.html",
        form=form,
        uploaded_files=uploaded_documents,
        user_documents=user_documents
    )

def _load_user_documents():
    """Load all documents uploaded by the currently logged-in user."""

    user_id = session.get("user_id")

    if not user_id:
        return []

    try:
        response = (
            supabase_admin
            .table("user_documents")
            .select("*")
            .eq("user_id", user_id)
            .order("uploaded_at", desc=True)
            .execute()
        )

        return response.data or []

    except Exception:
        logger.exception(
            "Failed to load user documents for user %s",
            user_id
        )

        return []

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
