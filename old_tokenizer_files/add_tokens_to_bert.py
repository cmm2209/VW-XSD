import json
import re

# Read the extracted en_tokens
with open('en_tokens.json', 'r', encoding='utf-8') as f:
    en_tokens = json.load(f)

print(f'Loaded {len(en_tokens)} tokens to add')

# Read BERTtokenizer.json
with open('BERTtokenizer.json', 'r', encoding='utf-8') as f:
    bert_content = f.read()

# Fix any trailing commas in BERTtokenizer.json
bert_content = re.sub(r',(\s*})', r'\1', bert_content)

# Parse the fixed JSON
bert_data = json.loads(bert_content)

# Get the current vocab and find the highest token ID
vocab = bert_data['model']['vocab']
max_id = max(vocab.values()) if vocab else -1
print(f'Highest current token ID: {max_id}')

# Add the new tokens with sequential IDs starting from max_id + 1
next_id = max_id + 1
for token, old_id in en_tokens.items():
    vocab[token] = next_id
    next_id += 1

print(f'Added {len(en_tokens)} tokens with IDs from {max_id + 1} to {next_id - 1}')

# Save the updated BERTtokenizer.json
with open('BERTtokenizer.json', 'w', encoding='utf-8') as f:
    json.dump(bert_data, f, indent=2, ensure_ascii=False)

print('Updated BERTtokenizer.json saved successfully')