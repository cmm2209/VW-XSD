#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
quotation_tagger.py

Tags each word of each quotation: 
    ¿ for Beginning of quotation, 
    % for Inside of quotation,
    € for End of quotation,
    $ for Single-word quotation.


Counts characters between utterances and insert that count after the end of each.

Usage (PowerShell, CMD, Bash, etc.):
    python qtag-character-count.py >base_name<

Example:
    python qtag-character-count.py myfile 
    # reads myfile.txt, writes myfile-quote-tag.txt
"""

import sys
import pathlib
import re

def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 2:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} >base_name<", file=sys.stderr)
        sys.exit(1)

    base_name = sys.argv[1]

    txt_path = pathlib.Path(f"{base_name}.txt")
    txt_tag_path = pathlib.Path(f"{base_name}-quote-tag.txt")

    if not txt_path.is_file():
        print(f"Error: '{txt_path}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # ------------------------------------------------------------------
    # 2️⃣  Read the .txt file 
    # ------------------------------------------------------------------
    replacements = {
        r'<\s*':    '<',     # Remove whitespace after <
        r'\s*>':    '>',     # Remove whitespace before >
        r'([^\s])<': r'\1 <', # Ensure space before <
        r'>([^\s])': r'> \1'  # Ensure space after >
    }
    with txt_path.open('r', encoding='utf-8') as file:
        content = file.read()
    
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
    
       # ------------------------------------------------------------------
    # 3️⃣  Process the content - tag quotation words
    # ------------------------------------------------------------------
    lines = content.split('\n')
    output_lines = []
    in_quote = False
    
    for line in lines:
        words = line.split(' ')
        output_words = []
        
        for word in words:
            if word == '':
                output_words.append(word)
                continue
                
            if not in_quote:
                if '<' in word:
                    in_quote = True
                    if '>' in word:
                        # Single-word quotation
                        in_quote = False
                    output_words.append(word)
                else:
                    output_words.append(word)
            else:
                if '>' in word:
                    # End of quotation — remove > and prepend €
                    in_quote = False
                else:
                    # Inside quotation
                    word = '%' + word
                output_words.append(word)
        
        output_lines.append(' '.join(output_words))
    
    tagged_content = '\n'.join(output_lines)  # ✅ Moved outside the loop
    
    # ------------------------------------------------------------------
    # 3.5️⃣  Insert character counts after each >
    # ------------------------------------------------------------------
    result = []
    i = 0
    while i < len(tagged_content):
        result.append(tagged_content[i])
        if tagged_content[i] == '>':
            j = i + 1
            count = 0
            while j < len(tagged_content) and tagged_content[j] != '<':
                count += 1
                j += 1
            result.append(str(count))
        i += 1
    
    final_content = ''.join(result)
    
    # ------------------------------------------------------------------
    # 4️⃣  Write output
    # ------------------------------------------------------------------
    with txt_tag_path.open('w', encoding='utf-8') as file:
        file.write(final_content)  # ✅ final_content not tagged_content
        
    print(f"Successfully processed '{txt_path}' -< '{txt_tag_path}'")

if __name__ == '__main__':
    main()