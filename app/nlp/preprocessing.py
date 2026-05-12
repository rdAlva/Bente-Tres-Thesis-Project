from nltk.tokenize import word_tokenize
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

directory_path = SCRIPT_DIR.parent / "utils" / "txtFileUpload"

print(f"Checking path: {directory_path}") #not sure if kasama

if directory_path.exists() and directory_path.is_dir():
    for file_path in directory_path.iterdir():
        if file_path.is_file():
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read().lower()
                print("")
                print(f"Successfully read: {file_path.name}")
                sentences = sent_tokenize(text)

                tokens = [word_tokenize(sentences) for sentences in sentences ]
                english_stops = stopwords.words("english")
                stopword_filter = lambda word : word.lower() not in english_stops
                sentences_filtered =[]

                for tokens in tokens:
                    sentences_filtered = list(filter(stopword_filter, tokens))
                    sentences_filtered.append(sentences_filtered)
                    print(sentences_filtered)

else:
    print(f"Directory not found at: {directory_path}")






