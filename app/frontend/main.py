from app.services.detector import run_detection
from app.services.review import load_review_report
from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from werkzeug.utils import secure_filename
import os
import shutil
from pathlib import Path
from wtforms.validators import InputRequired
from wtforms import MultipleFileField
from app.services.repository import upload_repository
from flask import redirect, url_for

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)
LASTEST_RESULTS = None
print("Flask app created.")
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'static',
    'file'
)
app.config['SECRET_KEY'] = 'supersecretkey' #to be changed
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
TXT_UPLOAD_FOLDER = (
    Path(__file__).resolve().parent.parent
    / "utils"
    / "txtFileUpload"
)
print("UPLOAD_FOLDER =", UPLOAD_FOLDER)
print("Exists?", os.path.exists(UPLOAD_FOLDER))

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

class UploadFileForm(FlaskForm):
    files = MultipleFileField(
        "Files",
        validators=[InputRequired()]
    )

    submit = SubmitField("Upload Files")

class RepositoryUploadForm(FlaskForm):

    files = MultipleFileField(
        "Repository Files",
        validators=[InputRequired()]
    )

    submit = SubmitField("Add to Repository")

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])

def home():

    print("Route accessed")

    form = UploadFileForm()

    print("Request method:", request.method)

    if request.method == "POST":
        print("POST RECEIVED")
        print("request.files =", request.files)

    print("Form validation:", form.validate_on_submit())
    print("Form errors:", form.errors)

    if form.validate_on_submit():

        print("FORM VALIDATED")
        clear_upload_folders()

        for file in form.files.data:

            filename = secure_filename(file.filename)

            save_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            file.save(save_path)
            print("Saved:", filename)
            print("Saved to:", save_path)

        results = run_detection()
        global LAST_RESULTS
        LAST_RESULTS = results

        return render_template(
            "results.html",
            uploaded_files=results["uploaded_files"],
            total_uploaded=results["total_uploaded"],
            total_repository=results["total_repository"],
            results=results["results"]
        )
    return render_template(
    "index.html",
    form=form
    )

@app.route("/review/<filename>")
def review(filename):

    report = load_review_report(filename)

    return render_template(
        "review.html",
        review=report
    )

@app.route("/results")
def results():

    global LAST_RESULTS

    if LAST_RESULTS is None:
        return redirect(url_for("home"))

    return render_template(
        "results.html",
        uploaded_files=LAST_RESULTS["uploaded_files"],
        total_uploaded=LAST_RESULTS["total_uploaded"],
        total_repository=LAST_RESULTS["total_repository"],
        results=LAST_RESULTS["results"]
    )

@app.route("/repository", methods=["GET", "POST"])
def repository():

    form = RepositoryUploadForm()

    if form.validate_on_submit():

        for file in form.files.data:

            filename = secure_filename(file.filename)

            save_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            file.save(save_path)

            print("Repository upload:", filename)

        uploaded_files = upload_repository()

        return render_template(
            "repository.html",
            form=form,
            uploaded_files=uploaded_files
        )

    return render_template(
        "repository.html",
        form=form,
        uploaded_files=[]
    )


print("main.py finished importing.")
if __name__ == '__main__':
    app.run(debug=True)
