from tokenizers import Tokenizer
import sys

tokenizer_file = sys.argv[1]

# Load your tokenizer
tokenizer = Tokenizer.from_file(tokenizer_file)

# Load your sample text
with open("token_test_corpus.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Split text into words (whitespace-delimited)
words = text.split()

# Encode the full text
encoding = tokenizer.encode(text)
num_tokens = len(encoding.ids)

# Calculate fertility: tokens per word
num_words = len(words)
fertility = num_tokens / num_words

print(f"Number of words: {num_words}")
print(f"Number of tokens: {num_tokens}")
print(f"Fertility (tokens/word): {fertility:.4f}")