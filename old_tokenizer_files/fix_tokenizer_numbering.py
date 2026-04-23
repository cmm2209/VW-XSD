import json
import re

# Read BERTtokenizer.json
with open('BERTtokenizer.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix any trailing commas
content = re.sub(r',(\s*})', r'\1', content)

# Parse the JSON
data = json.loads(content)

# Get the vocab
vocab = data['model']['vocab']

# Convert to list of (token, id) pairs to analyze
token_list = list(vocab.items())

print(f"Total tokens in vocab: {len(token_list)}")

# Find tokens with ID <= 30010
preserved_tokens = {k: v for k, v in token_list if v <= 30010}
print(f"Tokens with ID <= 30010: {len(preserved_tokens)}")

# Find tokens with ID > 30010
tokens_to_renumber = {k: v for k, v in token_list if v > 30010}
print(f"Tokens with ID > 30010: {len(tokens_to_renumber)}")

# Check for duplicates in the preserved section
preserved_ids = list(preserved_tokens.values())
if len(preserved_ids) != len(set(preserved_ids)):
    print("WARNING: Found duplicate IDs in preserved section!")
    from collections import Counter
    duplicates = [id for id, count in Counter(preserved_ids).items() if count > 1]
    print(f"Duplicate IDs: {duplicates}")

# Check for duplicates in the to-be-renumbered section
renumber_ids = list(tokens_to_renumber.values())
if len(renumber_ids) != len(set(renumber_ids)):
    print("WARNING: Found duplicate IDs in tokens to be renumbered!")
    from collections import Counter
    duplicates = [id for id, count in Counter(renumber_ids).items() if count > 1]
    print(f"Duplicate IDs: {duplicates}")

# Find the maximum ID in the preserved section
max_preserved_id = max(preserved_ids) if preserved_ids else -1
print(f"Maximum preserved ID: {max_preserved_id}")

# Create a new vocab with preserved tokens and renumbered tokens
new_vocab = {}

# Add all preserved tokens (ID <= 30010)
for token, token_id in preserved_tokens.items():
    new_vocab[token] = token_id

# Renumber tokens that were > 30010
next_id = max_preserved_id + 1
for token, old_id in sorted(tokens_to_renumber.items(), key=lambda x: x[1]):
    new_vocab[token] = next_id
    next_id += 1

print(f"Renumbered {len(tokens_to_renumber)} tokens from {max_preserved_id + 1} to {next_id - 1}")

# Update the vocab in the data structure
data['model']['vocab'] = new_vocab

# Save the corrected JSON
with open('BERTtokenizer.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Fixed BERTtokenizer.json saved successfully")

# Verify the fix
print("\nVerification:")
print(f"Total tokens after fix: {len(new_vocab)}")
print(f"Token IDs range from {min(new_vocab.values())} to {max(new_vocab.values())}")

# Check for any remaining duplicates
all_ids = list(new_vocab.values())
if len(all_ids) != len(set(all_ids)):
    print("ERROR: Still have duplicate IDs!")
    from collections import Counter
    duplicates = [id for id, count in Counter(all_ids).items() if count > 1]
    print(f"Duplicate IDs: {duplicates}")
else:
    print("No duplicate IDs found - numbering is correct!")