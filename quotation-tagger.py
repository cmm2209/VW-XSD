#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
quotation_tagger.py

Tags each word of each quotation: $ for start of quotation, % for subsequent words.
Also counts characters between < and the next > and inserts that count after <.

Usage (PowerShell, CMD, Bash, etc.):
    python quotation-tagger.py <base_name>

Example:
    python quotation-tagger.py myfile 
    # reads myfile.txt, writes myfile-quote-tag.txt
"""

import sys
import pathlib

def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 2:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <base_name>", file=sys.stderr)
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
    with txt_path.open('r', encoding='utf-8') as file:
        content = file.read()
    
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
                # Preserve multiple spaces
                output_words.append(word)
                continue
                
            if not in_quote:
                if '>' in word:
                    # Start of a quotation — insert $ after >
                    word = word.replace('>', '>$', 1)
                    in_quote = True
                    # Check if this same word also ends the quote
                    if '<' in word:
                        in_quote = False
                    output_words.append(word)
                else:
                    # Outside a quotation — keep as-is
                    output_words.append(word)
            else:
                # Inside a quotation — prepend % to the word
                word = '%' + word
                # Check if this word ends the quote
                if '<' in word:
                    in_quote = False
                output_words.append(word)
        
        output_lines.append(' '.join(output_words))
    
    # ------------------------------------------------------------------
    # 3.5️⃣  Insert character counts between < and the next >
    # ------------------------------------------------------------------
    tagged_content = '\n'.join(output_lines)
    
    result = []
    i = 0
    while i < len(tagged_content):
        result.append(tagged_content[i])
        if tagged_content[i] == '<':
            # Count characters from here until the next '>' (exclusive of < and >)
            j = i + 1
            count = 0
            while j < len(tagged_content) and tagged_content[j] != '>':
                count += 1
                j += 1
            # Insert the count immediately after '<'
            result.append(str(count))
        i += 1
    
    final_content = ''.join(result)
    
    # ------------------------------------------------------------------
    # 4️⃣  Write the processed content to the output file
    # ------------------------------------------------------------------
    with txt_tag_path.open('w', encoding='utf-8') as file:
        file.write(final_content)
    
    print(f"Successfully processed '{txt_path}' -> '{txt_tag_path}'")

if __name__ == '__main__':
    main()