import json
import re

# Read and fix the oldtokenizer.json
with open('oldBERTtokenizer.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove trailing comma before closing brace
content = re.sub(r',(\s*})', r'\1', content)

# Parse the fixed JSON
data = json.loads(content)

# Extract tokens starting with Ġen
vocab = data['model']['vocab']
en_tokens = {k: v for k, v in vocab.items() if k.startswith('Ġen')}

print(f'Found {len(en_tokens)} tokens starting with Ġen')

# Save the extracted tokens
with open('en_tokens.json', 'w', encoding='utf-8') as f:
    json.dump(en_tokens, f, indent=2, ensure_ascii=False)

print('Extracted tokens saved to en_tokens.json')