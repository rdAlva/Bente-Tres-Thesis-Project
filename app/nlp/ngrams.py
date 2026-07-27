def generate_ngrams(text, n):
    """
    Generate n-grams from preprocessed text.

    Args:
        text (str): Preprocessed document text.
        n (int): Size of the n-gram.

    Returns:
        list[tuple]: List of n-grams.
    """

    if not text or n <= 0:
        return []

    tokens = text.split()

    return [
        tuple(tokens[i:i + n])
        for i in range(len(tokens) - n + 1)
    ]