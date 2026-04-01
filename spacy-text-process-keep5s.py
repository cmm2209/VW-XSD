import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token

import sys
import pathlib
import re

Token.set_extension("line_number", default=None, force=True)

def main():
    # ------------------------------------------------------------------
    # 1️⃣  Get the base filename from the command line
    # ------------------------------------------------------------------
    if len(sys.argv) != 2:
        prog = pathlib.Path(sys.argv[0]).name
        print(f"Usage: python {prog} <base_name>", file=sys.stderr)
        sys.exit(1)

    base_name = sys.argv[1]

    # Build full input / output paths (same folder as the script is run from)
    txt_path = pathlib.Path(f"{base_name}.txt")
    
    if not txt_path.is_file():
        print(f"Error: '{txt_path}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # ------------------------------------------------------------------
    # 2️⃣  Read the .txt file and process line numbers
    # ------------------------------------------------------------------
    with txt_path.open('r', encoding='utf-8') as file:
        original_lines = file.readlines()
    
    # Process lines: skip @ lines, validate and remove line numbers
    processed_lines = []
    line_num = 0  # Track line numbers for non-@ lines
    
    for line in original_lines:
        # Skip lines that start with @
        if line.strip().startswith('@'):
            processed_lines.append(line)
            continue
        
        line_num += 1
        
        # Check if this is every 5th line (5, 10, 15, 20, etc.)
        if line_num % 5 == 0:
            # This line should have a number at the start
            # Extract the number
            match = re.match(r'^\s*(\d{1,6})\s+', line)
            if not match:
                raise ValueError(f"Error at line {line_num}: expected line number, but none found")
            
            extracted_num = int(match.group(1))
            
            # Validate the number matches the expected sequence
            if extracted_num != line_num:
                raise ValueError(f"Error at line {line_num}: expected {line_num}, found {extracted_num}")
            
            # Remove the line number from the line
            line = re.sub(r'^\s*\d{1,6}\s+', '', line)
        
        processed_lines.append(line)
    
    # Join the processed lines back into text
    text = ''.join(processed_lines)
    
    # Load Spacy model
    nlp = spacy.load("de_core_news_sm")

    @Language.component("line_number_parse")
    def line_number_parser(doc):
        # Track character positions of each line
        char_positions = []
        current_pos = 0
        
        for line in processed_lines:
            line_start = current_pos
            line_end = current_pos + len(line)
            char_positions.append((line_start, line_end, line))
            current_pos = line_end
        
        # Track line numbers for non-@ lines
        line_num = 0
        
        # Process each line and assign line numbers to tokens
        for line_start, line_end, line in char_positions:
            # Skip @ lines
            if line.strip().startswith('@'):
                continue
            
            line_num += 1
            
            # Assign line number to tokens in this line
            for token in doc:
                if line_start <= token.idx < line_end:
                    token._.line_number = line_num
        
        return doc

    nlp.add_pipe("line_number_parse", first=True)
    
    # Process the text with Spacy
    doc = nlp(text)

    # Print tokens with their line numbers
    for sent in doc.sents:
        for token in sent:
            line_num = token._.line_number or "N/A"
            print(f"Token: '{token.text}' | POS: '{token.pos_}' | Line: {line_num}")


if __name__ == '__main__':
    main()