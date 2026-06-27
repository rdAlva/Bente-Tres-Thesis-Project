from pathlib import Path
from app.nlp.preprocessing import preprocess_text

def generate_ngrams(text, n):
    tokens = text.split()
    ngrams = [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
    return ngrams


# Directory Processing Logic
SCRIPT_DIR = Path(__file__).resolve().parent
directory_path = SCRIPT_DIR.parent / "utils" / "txtFileUpload"

corpus = []
filenames = []

# Read ALL txt files
for txt_file in directory_path.glob("*.txt"):

    processed_text = preprocess_text(txt_file)

    corpus.append(processed_text)
    filenames.append(txt_file.name)


# Only runs if this file is executed directly
if __name__ == "__main__":

    for i, text in enumerate(corpus):

        unigrams = generate_ngrams(text, 1)
        bigrams = generate_ngrams(text, 2)
        trigrams = generate_ngrams(text, 3)

        print(f"\nFile: {filenames[i]}")
        print("Unigrams:", unigrams[:10])
        print("Bigrams:", bigrams[:10])
        print("Trigrams:", trigrams[:10])