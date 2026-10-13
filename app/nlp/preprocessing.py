import nltk
import string
from pathlib import Path
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Pre-load resources
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('stopwords')

stemmer = PorterStemmer()

def preprocess_text(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Normalization: Lowercase and strip punctuation
            raw_text = f.read().lower()
            clean_text = raw_text.translate(str.maketrans('', '', string.punctuation))

            # Tokenization
            sentences = sent_tokenize(clean_text)
            stop_words = set(stopwords.words("english"))

            document_tokens = []
            for sentence in sentences:
                words = word_tokenize(sentence)
                # Filter stop words and non-alphanumeric noise
                filtered = [
                    stemmer.stem(w)
                    for w in words
                    if w not in stop_words and w.isalnum()
                ]
                document_tokens.extend(filtered)

            # Convert token list back to string
            return " ".join(document_tokens)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return [].lower()

# Directory Processing Logic
SCRIPT_DIR = Path(__file__).resolve().parent
directory_path = SCRIPT_DIR.parent / "utils" / "txtFileUpload"
corpus_path = SCRIPT_DIR.parent.parent / "corpus" / "promoted"

if __name__ == "__main__":
    if directory_path.exists():
        for txt_file in directory_path.glob("*.txt"):
            tokens = preprocess_text(txt_file)
            print(f"Processed {txt_file.name}: {len(tokens)} tokens.")

    if corpus_path.exists():
        for txt_file in corpus_path.glob("*.txt"):
            tokens = preprocess_text(txt_file)
            print(f"Processed {txt_file.name}: {len(tokens)} tokens.")