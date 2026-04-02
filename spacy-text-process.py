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
    # 2️⃣  Read the .txt file
    # ------------------------------------------------------------------
    with txt_path.open('r', encoding='utf-8') as file:
        original_lines = file.readlines()
    
    # ------------------------------------------------------------------
    # 3️⃣  Identify @ lines
    # ------------------------------------------------------------------
    is_at_line = [line.strip().startswith('@') for line in original_lines]
    
    # ------------------------------------------------------------------
    # 4️⃣  Extract line-starting numbers for validation
    # ------------------------------------------------------------------
    line_starting_numbers = {}  # Maps line index to extracted number
    for idx, line in enumerate(original_lines):
        if is_at_line[idx]:
            continue
        match = re.match(r'^\s*(\d{1,6})\s+', line)
        if match:
            line_starting_numbers[idx] = int(match.group(1))
    
    # Get sorted list of indices that have line-starting numbers
    numbered_indices = sorted(line_starting_numbers.keys())
    
    # ------------------------------------------------------------------
    # 5️⃣  Assign line numbers with restart detection
    # ------------------------------------------------------------------
    line_numbers = {}  # Maps line index to assigned line number
    current_line_num = 0
    i = 0  # Index in numbered_indices
    
    for idx, line in enumerate(original_lines):
        if is_at_line[idx]:
            continue
        
        current_line_num += 1
        line_numbers[idx] = current_line_num
        
        # Check if this line has a starting number
        if idx in line_starting_numbers:
            starting_num = line_starting_numbers[idx]
            
            # Check if the starting number matches the assigned number
            if starting_num != current_line_num:
                # Step 5: Check if it's 5
                if starting_num != 5:
                    raise ValueError(f"Error at line {current_line_num}: expected {current_line_num}, found {starting_num}")
                
                # Step 6: Check if the next line-starting number is 10
                # Find the next numbered line
                next_idx = None
                for next_num_idx in numbered_indices:
                    if next_num_idx > idx:
                        next_idx = next_num_idx
                        break
                
                if next_idx is None:
                    raise ValueError(f"Error at line {current_line_num}: found 5 but no following numbered line to check for 10")
                
                next_starting_num = line_starting_numbers[next_idx]
                
                if next_starting_num != 10:
                    raise ValueError(f"Error at line {current_line_num}: found 5 but next numbered line has {next_starting_num}, not 10")
                
                # Step 7: 5 followed by 10 means restart
                # Count back 4 lines from the line starting with 5
                restart_index = idx
                lines_back = 0
                while lines_back < 4 and restart_index >= 0:
                    restart_index -= 1
                    if not is_at_line[restart_index]:
                        lines_back += 1
                
                # Go back to line 40 (restart the line assigning procedure)
                # Clear line numbers from restart_index onwards
                for clear_idx in range(restart_index, len(original_lines)):
                    if clear_idx in line_numbers:
                        del line_numbers[clear_idx]
                
                # Restart numbering from restart_index
                current_line_num = 0
                for re_idx in range(restart_index, idx + 1):
                    if is_at_line[re_idx]:
                        continue
                    current_line_num += 1
                    line_numbers[re_idx] = current_line_num
                
                # Continue from the next line after the 5
                # The loop will continue naturally from idx+1
    
    # ------------------------------------------------------------------
    # 6️⃣  Clean up the text (remove @ symbols and line numbers)
    # ------------------------------------------------------------------
    cleaned_lines = []
    for idx, line in enumerate(original_lines):
        if is_at_line[idx]:
            # Remove the @ symbol and any whitespace after it
            line = re.sub(r'^\s*@\s*', '', line)
        else:
            # Remove line-starting numbers
            line = re.sub(r'^\s*\d{1,6}\s+', '', line)
        cleaned_lines.append(line)
    
    # Join the cleaned lines back into text
    text = ''.join(cleaned_lines)
    
    # ------------------------------------------------------------------
    # 7️⃣  Load Spacy model and process
    # ------------------------------------------------------------------
    nlp = spacy.load("de_core_news_sm")

    @Language.component("line_number_parse")
    def line_number_parser(doc):
        # Track character positions of each line
        char_positions = []
        current_pos = 0
        
        for line in cleaned_lines:
            line_start = current_pos
            line_end = current_pos + len(line)
            char_positions.append((line_start, line_end, line))
            current_pos = line_end
        
        # Process each line and assign line numbers to tokens
        for idx, (line_start, line_end, line) in enumerate(char_positions):
            # Skip lines that were originally @ lines
            if is_at_line[idx]:
                continue
            
            # Get the line number for this line
            line_num = line_numbers[idx]
            
            # Assign line number to tokens in this line
            for token in doc:
                if line_start <= token.idx < line_end:
                    token._.line_number = line_num
        
        return doc

    nlp.add_pipe("line_number_parse", first=True)
    
    # Process the text with Spacy
    doc = nlp(text)

    # ------------------------------------------------------------------
    # 8️⃣  Print tokens with their line numbers
    # ------------------------------------------------------------------
    for sent in doc.sents:
        for token in sent:
            line_num = token._.line_number or "N/A"
            print(f"Token: '{token.text}' | POS: '{token.pos_}' | Line: {line_num}")


if __name__ == '__main__':
    main()