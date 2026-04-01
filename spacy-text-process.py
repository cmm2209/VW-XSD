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
    
    # Track which lines are @ lines
    is_at_line = [line.strip().startswith('@') for line in original_lines]
    
    # First pass: identify which lines have numbers and extract them
    # Skip @ lines entirely
    numbered_lines = {}  # Maps line index to extracted number
    for idx, line in enumerate(original_lines):
        if is_at_line[idx]:
            continue
        match = re.match(r'^\s*(\d{1,6})\s+', line)
        if match:
            numbered_lines[idx] = int(match.group(1))
    
    # Second pass: process lines with restart detection
    # Skip @ lines entirely
    processed_lines = []
    line_num = 0  # Track line numbers for non-@ lines
    numbered_indices = sorted(numbered_lines.keys())
    
    for idx, line in enumerate(original_lines):
        # Skip @ lines entirely
        if is_at_line[idx]:
            processed_lines.append(line)
            continue
        
        line_num += 1
        
        # Check if this line has a number
        if idx in numbered_lines:
            extracted_num = numbered_lines[idx]
            
            # Check if this is every 5th line (5, 10, 15, 20, etc.)
            if line_num % 5 == 0:
                # Validate the number matches the expected sequence
                if extracted_num != line_num:
                    # Unexpected number - check for restart
                    if extracted_num == 5:
                        # Scan ahead to find the next numbered line
                        next_num = None
                        for next_idx in numbered_indices:
                            if next_idx > idx:
                                next_num = numbered_lines[next_idx]
                                break
                        
                        if next_num == 10:
                            # This is a restart - backtrack 4 lines and restart from 1
                            # Remove the last 4 lines from processed_lines
                            for _ in range(4):
                                if processed_lines:
                                    processed_lines.pop()
                            
                            # Reset line_num to 0 (will become 1 after increment)
                            line_num = 0
                            
                            # Remove the line number from the line
                            line = re.sub(r'^\s*\d{1,6}\s+', '', line)
                            processed_lines.append(line)
                            continue
                        else:
                            raise ValueError(f"Error at line {line_num}: expected {line_num}, found {extracted_num}, but next numbered line is {next_num}, not 10")
                    else:
                        raise ValueError(f"Error at line {line_num}: expected {line_num}, found {extracted_num}")
                
                # Remove the line number from the line
                line = re.sub(r'^\s*\d{1,6}\s+', '', line)
        else:
            # This line doesn't have a number
            # Check if we expected one (every 5th line)
            if line_num % 5 == 0:
                # Expected a number but didn't find one - this might be before a restart
                # Continue processing, the restart detection will handle it
                pass
        
        processed_lines.append(line)
    
    # Third pass: remove @ symbols from all lines
    final_lines = []
    for idx, line in enumerate(processed_lines):
        if is_at_line[idx]:
            # Remove the @ symbol and any whitespace after it
            line = re.sub(r'^\s*@\s*', '', line)
        final_lines.append(line)
    
    # Join the processed lines back into text
    text = ''.join(final_lines)
    
    # Load Spacy model
    nlp = spacy.load("de_core_news_sm")

    @Language.component("line_number_parse")
    def line_number_parser(doc):
        # Track character positions of each line
        char_positions = []
        current_pos = 0
        
        for line in final_lines:
            line_start = current_pos
            line_end = current_pos + len(line)
            char_positions.append((line_start, line_end, line))
            current_pos = line_end
        
        # Track line numbers for non-@ lines
        line_num = 0
        
        # Process each line and assign line numbers to tokens
        for idx, (line_start, line_end, line) in enumerate(char_positions):
            # Skip lines that were originally @ lines
            # is_at_line is accessible here via closure
            if is_at_line[idx]:
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