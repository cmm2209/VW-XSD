from tokenizers import Tokenizer

# Load the tokenizer
tokenizer = Tokenizer.from_file("your_tokenizer.json")

# Add new tokens
new_words = ["myword1", "myword2", "myword3"]
tokenizer.add_tokens(new_words)

# Save the modified tokenizer
tokenizer.save("your_tokenizer_modified.json")