#!/usr/bin/env python3
"""
Remove contractions from BERT tokenizer vocabulary.

This script reads a list of contractions from REM_contractions_to_do.json
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


def extract_contraction_forms(contractions_file):
    """Extract all 'form' values from the contractions JSON file."""
    contractions_data = load_json_file(contractions_file)
    forms = set()
    
    for entry in contractions_data:
        if 'form' in entry:
            forms.add(entry['form'])
    
    return forms


def remove_contractions_from_vocab(tokenizer_file, contractions_forms):
    """Remove contractions from the tokenizer vocabulary."""
    tokenizer_data = load_json_file(tokenizer_file)
    
    # Access the vocabulary
    vocab = tokenizer_data['model']['vocab']
    
    # Track removed tokens
    removed_tokens = []
    
    # Remove tokens that match contractions
    for token in list(vocab.keys()):
        if token in contractions_forms:
            removed_tokens.append(token)
            del vocab[token]
    
    return tokenizer_data, removed_tokens


def main():
    # File paths
    tokenizer_file = 'BERTtokenizer.json'
    contractions_file = 'REM_common_contractions.json'
    backup_file = 'BERTtokenizer.json.backup'
    
    print("Loading contractions file...")
    contractions_forms = extract_contraction_forms(contractions_file)
    print(f"Found {len(contractions_forms)} unique contractions")
    
    print("\nLoading tokenizer file...")
    
    # Create backup
    print(f"Creating backup: {backup_file}")
    shutil.copy2(tokenizer_file, backup_file)
    
    # Remove contractions
    print("Removing contractions from vocabulary...")
    tokenizer_data, removed_tokens = remove_contractions_from_vocab(tokenizer_file, contractions_forms)
    
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