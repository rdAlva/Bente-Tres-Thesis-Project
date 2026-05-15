import os
import pathlib
import pymupdf

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
pdf_folder = os.path.join(BASE_DIR, "static", "file")
txt_folder = os.path.join(BASE_DIR, "utils", "txtFileUpload")
os.makedirs(txt_folder, exist_ok=True)

# loop through PDFs
for filename in os.listdir(pdf_folder):

    if filename.endswith(".pdf"):

        pdf_path = os.path.join(pdf_folder, filename)

        # extract PDF text
        with pymupdf.open(pdf_path) as doc:

            text = chr(12).join(
                [page.get_text() for page in doc]
            )

        # create txt filename
        txt_filename = os.path.splitext(filename)[0] + ".txt"

        txt_path = os.path.join(
            txt_folder,
            txt_filename
        )

        # save txt file
        pathlib.Path(txt_path).write_bytes(
            text.encode()
        )

        print(f"Converted: {filename} -> {txt_filename}")