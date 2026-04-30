#!/usr/bin/env python3
"""
Remove tokens from BERT tokenizer vocabulary.

This script reads whitespace-separated words from a text file
and removes any matching tokens from the vocabulary in BERTtokenizer.json.
"""

import json
import shutil
from pathlib import Path


def load_json_file(filepath):
    """Load a JSON file and return its contents."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data, filepath):
    """Save data to a JSON file with proper formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_words_from_text(text_file):
    """Load whitespace-separated words from a text file."""
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    words = set(content.split())
    return words


def remove_tokens_from_vocab(tokenizer_file, tokens_to_remove):
    """Remove specified tokens from the tokenizer vocabulary."""
    tokenizer_data = load_json_file(tokenizer_file)
    
    # Access the vocabulary
    vocab = tokenizer_data['model']['vocab']
    
    # Track removed tokens
    removed_tokens = []
    
    # Remove tokens that match words from the text file
    for token in list(vocab.keys()):
        if token in tokens_to_remove:
            removed_tokens.append(token)
            del vocab[token]
    
    return tokenizer_data, removed_tokens


def main():
    # File paths
    tokenizer_file = 'BERTtokenizer.json'
    words_file = 'tokenizertest.txt'
    backup_file = 'BERTtokenizer.json.backup'
    
    print(f"Loading words from {words_file}...")
    words_to_remove = load_words_from_text(words_file)
    print(f"Found {len(words_to_remove)} unique words")
    
    print("\nLoading tokenizer file...")
    
    # Create backup
    print(f"Creating backup: {backup_file}")
    shutil.copy2(tokenizer_file, backup_file)
    
    # Remove matching tokens
    print("Removing matching tokens from vocabulary...")
    tokenizer_data, removed_tokens = remove_tokens_from_vocab(tokenizer_file, words_to_remove)
    
    print(f"\nRemoved {len(removed_tokens)} tokens from vocabulary:")
    for token in removed_tokens[:20]:  # Show first 20
        print(f"  - {token}")
    if len(removed_tokens) > 20:
        print(f"  ... and {len(removed_tokens) - 20} more")
    
    # Save modified tokenizer
    print(f"\nSaving modified tokenizer to {tokenizer_file}")
    save_json_file(tokenizer_data, tokenizer_file)
    
    print("\nDone!")


if __name__ == '__main__':
    main()