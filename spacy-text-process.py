import spacy
from spacy.language import Language
from spacy.tokens import Token, Doc
from tokenizers import Tokenizer
from text_replacements import load_replacements, apply_replacements 

import sys
import pathlib
import re
import unicodedata

Token.set_extension("line_number", default=None, force=True)
Token.set_extension("page_number", default=None, force=True)
Doc.set_extension("token_offsets", default=None, force=True)

new_tokenizer = Tokenizer.from_file("BERTtokenizer.json")

class BertTokenizer:
    SPECIAL_TOKENS = {"[CLS]", "[SEP]", "[PAD]", "[UNK]", "[MASK]"}

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
        
        filtered = [
            (tok, start, end)
            for tok, (start, end) in zip(tokens, offsets)
            if tok not in self.SPECIAL_TOKENS and (start, end) != (0, 0)
        ]

        if not filtered:
            doc = Doc(self.vocab, words=[], spaces=[])
            doc._.token_offsets = []
            return doc
            
        
        words = []
        spaces = []
        original_offsets = []

        for i, (tok, start, end) in enumerate(filtered):
            words.append(tok)
            original_offsets.append((start, end))
            if i < len(filtered) - 1:
                next_start = filtered[i + 1][1]
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
    line_numbers = {}
    last_assigned_num = 0

    for idx, line in enumerate(original_lines):
        if is_at_line[idx]:
            continue

        if idx in line_starting_numbers:
            raw_num = line_starting_numbers[idx]

            # ── Restart detection ─────────────────────────────────────
            # Only attempt a restart if the number is unexpected (i.e.
            # does not equal last_assigned_num + 1) AND is 5 or 10.
            expected_num = last_assigned_num + 1
            is_unexpected = raw_num != expected_num
            is_restart_candidate = raw_num in (5, 10)

            if is_unexpected and is_restart_candidate:
                if raw_num == 5:
                    # Confirm: next explicit number must be 10
                    next_idx = next(
                        (ni for ni in sorted(line_starting_numbers.keys()) if ni > idx),
                        None
                    )
                    if next_idx is None:
                        raise ValueError(
                            f"Line index {idx}: found unexpected '5' but no "
                            f"following numbered line to confirm restart (expected 10)."
                        )
                    if line_starting_numbers[next_idx] != 10:
                        raise ValueError(
                            f"Line index {idx}: found unexpected '5' but the next "
                            f"numbered line has {line_starting_numbers[next_idx]}, "
                            f"not 10 — cannot confirm restart."
                        )

                    # Walk back 4 non-@ lines to find where line 1 starts
                    restart_index = idx
                    lines_back = 0
                    while lines_back < 4 and restart_index > 0:
                        restart_index -= 1
                        if not is_at_line[restart_index]:
                            lines_back += 1

                    # Clear numbers already assigned from restart_index onward
                    for clear_idx in range(restart_index, len(original_lines)):
                        line_numbers.pop(clear_idx, None)

                    # Re-number from restart_index up to and including idx
                    current_line_num = 0
                    for re_idx in range(restart_index, idx + 1):
                        if is_at_line[re_idx]:
                            continue
                        current_line_num += 1
                        line_numbers[re_idx] = current_line_num

                    last_assigned_num = current_line_num  # == 5
                    continue

                elif raw_num == 10:
                    # Confirm: next explicit number must be 20
                    next_idx = next(
                        (ni for ni in sorted(line_starting_numbers.keys()) if ni > idx),
                        None
                    )
                    if next_idx is None:
                        raise ValueError(
                            f"Line index {idx}: found unexpected '10' but no "
                            f"following numbered line to confirm restart (expected 20)."
                        )
                    if line_starting_numbers[next_idx] != 20:
                        raise ValueError(
                            f"Line index {idx}: found unexpected '10' but the next "
                            f"numbered line has {line_starting_numbers[next_idx]}, "
                            f"not 20 — cannot confirm restart."
                        )

                    # Walk back 9 non-@ lines to find where line 1 starts
                    restart_index = idx
                    lines_back = 0
                    while lines_back < 9 and restart_index > 0:
                        restart_index -= 1
                        if not is_at_line[restart_index]:
                            lines_back += 1

                    # Clear numbers already assigned from restart_index onward
                    for clear_idx in range(restart_index, len(original_lines)):
                        line_numbers.pop(clear_idx, None)

                    # Re-number from restart_index up to and including idx
                    current_line_num = 0
                    for re_idx in range(restart_index, idx + 1):
                        if is_at_line[re_idx]:
                            continue
                        current_line_num += 1
                        line_numbers[re_idx] = current_line_num

                    last_assigned_num = current_line_num  # == 10
                    continue

            # ── Normal explicit number ────────────────────────────────
            # Unexpected but not a restart candidate, or expected: just
            # trust the number as written and assign it directly.
            line_numbers[idx] = raw_num
            last_assigned_num = raw_num

        else:
            # ── Unnumbered line ───────────────────────────────────────
            # No explicit number: infer as previous + 1
            inferred_num = last_assigned_num + 1
            line_numbers[idx] = inferred_num
            last_assigned_num = inferred_num

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
    nlp.tokenizer = BertTokenizer(nlp.vocab, new_tokenizer)

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
    for sent in doc.sents:
        for token in sent:
            line_num = token._.line_number or "N/A"
            page_num = token._.page_number or "N/A"
            print(f"Token: '{token.text}' | POS: '{token.pos_}' | Line: {line_num} | Page: {page_num}")

if __name__ == '__main__':
    main()