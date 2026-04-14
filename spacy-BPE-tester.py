import spacy
from spacy.language import Language
from spacy.tokens import Token, Doc
from transformers import PreTrainedTokenizerFast
from tokenizers import Tokenizer
from text_replacements import load_replacements, apply_replacements

import sys
import pathlib
import re
import unicodedata

Token.set_extension("line_number", default=None, force=True)
Token.set_extension("page_number", default=None, force=True)
Doc.set_extension("token_offsets", default=None, force=True)

new_tokenizer = Tokenizer.from_file("BPEtokenizer.json")

wrapped_tokenizer = PreTrainedTokenizerFast(
     tokenizer_object=new_tokenizer,
     unk_token="[UNK]",
)


class BPETokenizer:
    def __init__(self, vocab, tokenizer):
        self.vocab = vocab
        self._tokenizer = tokenizer
        self._tokenizer.no_padding()
        self._tokenizer.no_truncation()

    def __call__(self, text):
        original_text = text
        text = unicodedata.normalize("NFC", text)
        text = text.lower()
        encoding = self._tokenizer.encode(text)
        tokens = encoding.tokens
        offsets = encoding.offsets

        if not tokens:
            doc = Doc(self.vocab, words=[], spaces=[])
            doc._.token_offsets = []
            return doc
        
        words = []
        spaces = []
        original_offsets = []

        for i, (tok, (start, end)) in enumerate(zip(tokens, offsets)):
            words.append(tok)
            original_offsets.append((start, end))
            
            if i < len(tokens) - 1:
                next_start = offsets[i + 1][0]
                spaces.append(next_start > end)
            else:
                spaces.append(end < len(text) and text[end] == " ")
        doc = Doc(self.vocab, words=words, spaces=spaces)
        doc._.token_offsets = original_offsets
        return doc


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
    # 3️⃣  Identify @# lines and extract page numbers
    # ------------------------------------------------------------------
    page_numbers = {}  # Maps line index to page number
    current_page = None
    lines_to_delete = []  # Track @# line indices to delete
    
    for idx, line in enumerate(original_lines):
        stripped = line.strip()
        if stripped.startswith('@#'):
            # Extract page number from @# line
            match = re.match(r'^\s*@#\s*(\d+)', line)
            if match:
                current_page = int(match.group(1))
            lines_to_delete.append(idx)
        else:
            # Assign current page to this line
            if current_page is not None:
                page_numbers[idx] = current_page
    
    # Delete @# lines from original_lines (in reverse order to preserve indices)
    for idx in sorted(lines_to_delete, reverse=True):
        del original_lines[idx]
    
    # Rebuild page_numbers with corrected indices after deletion
    # Create a mapping from original indices to new indices
    original_to_new_index = {}
    new_idx = 0
    for original_idx in range(len(original_lines) + len(lines_to_delete)):
        if original_idx not in lines_to_delete:
            original_to_new_index[original_idx] = new_idx
            new_idx += 1
    
    # Build new page_numbers dictionary with corrected indices
    new_page_numbers = {}
    for original_idx, page_num in page_numbers.items():
        new_idx = original_to_new_index[original_idx]
        new_page_numbers[new_idx] = page_num
    
    page_numbers = new_page_numbers
    
    # ------------------------------------------------------------------
    # 4️⃣  Identify @ lines
    # ------------------------------------------------------------------
    is_at_line = [line.strip().startswith('@') for line in original_lines]
    
    # ------------------------------------------------------------------
    # 5️⃣  Extract line numbers (at start or end) for validation
    # ------------------------------------------------------------------
    line_starting_numbers = {}  # Maps line index to extracted number
    for idx, line in enumerate(original_lines):
        if is_at_line[idx]:
            continue
        # Check for number at start of line
        match = re.match(r'^\s*(\d{1,6})\s+', line)
        if match:
            line_starting_numbers[idx] = int(match.group(1))
        else:
            # Check for number at end of line
            match = re.search(r'\s*(\d{1,6})\s*$', line)
            if match:
                line_starting_numbers[idx] = int(match.group(1))
    
    # Get sorted list of indices that have line-starting numbers
    numbered_indices = sorted(line_starting_numbers.keys())
    
    # ------------------------------------------------------------------
    # 6️⃣  Assign line numbers with restart detection
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
                # Check if it's 5 or 10 (valid restart signals)
                if starting_num == 5:
                    # Check if the next line-starting number is 10
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
                    
                    # 5 followed by 10 means restart (every 5 lines)
                    # Count back 4 lines from the line starting with 5
                    restart_index = idx
                    lines_back = 0
                    while lines_back < 4 and restart_index >= 0:
                        restart_index -= 1
                        if not is_at_line[restart_index]:
                            lines_back += 1
                    
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
                    
                elif starting_num == 10:
                    # Check if the next line-starting number is 20
                    next_idx = None
                    for next_num_idx in numbered_indices:
                        if next_num_idx > idx:
                            next_idx = next_num_idx
                            break
                    
                    if next_idx is None:
                        raise ValueError(f"Error at line {current_line_num}: found 10 but no following numbered line to check for 20")
                    
                    next_starting_num = line_starting_numbers[next_idx]
                    
                    if next_starting_num != 20:
                        raise ValueError(f"Error at line {current_line_num}: found 10 but next numbered line has {next_starting_num}, not 20")
                    
                    # 10 followed by 20 means restart (every 10 lines)
                    # Count back 9 lines from the line starting with 10
                    restart_index = idx
                    lines_back = 0
                    while lines_back < 9 and restart_index >= 0:
                        restart_index -= 1
                        if not is_at_line[restart_index]:
                            lines_back += 1
                    
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
                    
                    # Continue from the next line after the 10
                    # The loop will continue naturally from idx+1
                    
                else:
                    raise ValueError(f"Error at line {current_line_num}: expected {current_line_num}, found {starting_num}")
    
    # ------------------------------------------------------------------
    # 7️⃣  Clean up the text (remove @ symbols and line numbers)
    # ------------------------------------------------------------------
    cleaned_lines = []
    for idx, line in enumerate(original_lines):
        if is_at_line[idx]:
            # Remove the @ symbol and any whitespace after it
            line = re.sub(r'^\s*@\s*', '', line)
        else:
            # Remove line numbers from start or end
            line = re.sub(r'^\s*\d{1,6}\s+', '', line)  # Remove from start
            line = re.sub(r'\s*\d{1,6}\s*$', '', line)  # Remove from end
        cleaned_lines.append(line)
    
    # Replace special characters using custom replacements list
    replacements = load_replacements("replacements.json")
    cleaned_lines = [apply_replacements(line, replacements) for line in cleaned_lines]
    
    # Join the cleaned lines back into text
    text = ''.join(cleaned_lines)
    
    # ------------------------------------------------------------------
    # 8️⃣  Load Spacy model and process
    # ------------------------------------------------------------------
    nlp = spacy.load("de_core_news_sm")
    nlp.tokenizer = BPETokenizer(nlp.vocab, new_tokenizer)

    @Language.component("line_number_parse")
    def line_number_parser(doc):
        # Track character positions of each line
        normalized_lines = [
            unicodedata.normalize("NFC", line).lower() 
            for line in cleaned_lines
        ]
        char_positions = []
        current_pos = 0
        
        for line in normalized_lines:
            line_start = current_pos
            line_end = current_pos + len(line)
            char_positions.append((line_start, line_end))
            current_pos = line_end
            
        token_offsets = doc._.token_offsets
        use_custom_offsets = token_offsets is not None and len(token_offsets) == len(doc)

        for i, token in enumerate(doc):
            if use_custom_offsets:
                tok_start = token_offsets[i][0]
            else:
                tok_start = token.idx

            # Find which line this token belongs to
            for idx, (line_start, line_end) in enumerate(char_positions):
                if line_start <= tok_start < line_end:
                    # Always assign the page number
                    token._.page_number = page_numbers.get(idx)
                    # Only assign line number for non-@ lines
                    if not is_at_line[idx]:
                        token._.line_number = line_numbers.get(idx)
                    break

        return doc

    nlp.add_pipe("line_number_parse", before="tagger")
    
    # Process the text with Spacy
    doc = nlp(text)

    # ------------------------------------------------------------------
    # 9️⃣  Print tokens with their line numbers and page numbers
    # ------------------------------------------------------------------
    with open('BPEtokens.txt', 'w', encoding='utf-8') as file:
        for token in doc:
            file.write(f"'{token.text}'\n")

if __name__ == '__main__':
    main()