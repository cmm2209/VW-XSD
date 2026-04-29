import spacy
from spacy.language import Language
from spacy.tokens import Token, Doc
from tokenizers import Tokenizer
from text_replacements import load_replacements, apply_replacements_with_mapping
from thinc.api import set_gpu_allocator, require_gpu
from transformers import AutoModelForMaskedLM
from spacy.cli.init_config import fill_config

import sys
import pathlib
import re
import unicodedata
import string

# Use the GPU, with memory allocations directed via PyTorch.
# This prevents out-of-memory errors that would otherwise occur from competing
# memory pools.
#set_gpu_allocator("pytorch")
#require_gpu(0)

model = AutoModelForMaskedLM.from_pretrained("christinbeck/GHisBERT")

Token.set_extension("line_number", default=None, force=True)
Token.set_extension("page_number", default=None, force=True)
Token.set_extension("paragraph_number", default=None, force=True)
Token.set_extension("book_number", default=None, force=True)
Token.set_extension("direct_speech", default=None, force=True)
Token.set_extension("original_form", default=None, force=True)
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
        # Apply replacements to get the normalized form for encoding
        # (text has already had replacements applied; we receive it ready to encode)
        normalized = unicodedata.normalize("NFC", text).lower()
        encoding = self._tokenizer.encode(normalized)
        tokens = encoding.tokens
        offsets = encoding.offsets

        if not tokens:
            doc = Doc(self.vocab, words=[], spaces=[])
            doc._.token_offsets = []
            return doc

        filtered = [
            (('##' if tok.startswith('##') else '') + text[start:end], start, end)
            for tok, (start, end) in zip(tokens, offsets)
            if tok not in self.SPECIAL_TOKENS
            and (start, end) != (0, 0)
            and text[start:end].strip() != ''
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
                spaces.append(end < len(normalized) and normalized[end] == " ")

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
    # 3️⃣  Identify @# lines and extract page and book numbers
    # ------------------------------------------------------------------
    page_numbers = {}  # Maps line index to page number
    book_numbers = {}
    current_page = None
    current_book = None
    lines_to_delete = []  # Track @# line indices to delete
    
    for idx, line in enumerate(original_lines):
        stripped = line.strip()
        if stripped.startswith('@'):
            if stripped.startswith("@#"):
                # Extract page number from @# line
                match = re.match(r'^\s*@#\s*(\d+)', line)
                if match:
                    current_page = int(match.group(1))
                lines_to_delete.append(idx)
            elif stripped.startswith('@£'):
                    # Extract book number from @# line
                match = re.match(r'^\s*@£\s*(\d+)', line)
                if match:
                    current_book = int(match.group(1))
                lines_to_delete.append(idx)
        else:
            # Assign current page to this line
            if current_page is not None:
                page_numbers[idx] = current_page
            if current_book is not None:
                book_numbers[idx] = current_book
    
    # Delete @ lines from original_lines (in reverse order to preserve indices)
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

    new_book_numbers = {}
    for original_idx, book_num in book_numbers.items():
        new_idx = original_to_new_index[original_idx]
        new_book_numbers[new_idx] = book_num
    
    book_numbers = new_book_numbers

    #Identify @ lines
    is_at_line = [line.strip().startswith('@') for line in original_lines]
    
    # ------------------------------------------------------------------
    # 4️⃣  Identify paragraph numbers
    # ------------------------------------------------------------------
    paragraph_numbers = {}   # Maps line index → paragraph number
    current_paragraph = 1

    for idx, line in enumerate(original_lines):
        # A line beginning with ¶ starts a new paragraph;
        # strip the marker so it doesn't appear in the cleaned text.
        if '¶' in line:
            original_lines[idx] = line.replace('¶', '')
            current_paragraph += 1
        paragraph_numbers[idx] = current_paragraph
    
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
            line = re.sub(r'^\s*@\s*', '', line)
        else:
            line = re.sub(r'^\s*\d{1,6}\s+', ' ', line)
            line = re.sub(r'\s*\d{1,6}\s*$', ' ', line)
        cleaned_lines.append(line)

    text = ''.join(cleaned_lines)

    # ------------------------------------------------------------------
    # 8️⃣  Split by spaces, assign direct speech and original_form,
    #       strip markers, then apply replacements
    # ------------------------------------------------------------------
    direct_speech_tags = {}  # keyed by char offset in final text
    original_forms = {}      # keyed by char offset in final text

    # We build the final text in two passes:
    # First pass: strip direct speech markers, record tags and original forms
    stripped_words = []
    current_pos = 0

    for word in re.split(r'(\s)', text):
        if not word:
            continue
        if word.startswith('¿'):
            tag = "Beginning"
            base_word = word[1:]
        elif word.startswith('%'):
            tag = "Inside"
            base_word = word[1:]
        elif word.startswith('€'):
            tag = "End"
            base_word = word[1:]
        elif word.startswith('$'):
            tag = "Singleton"
            base_word = word[1:]
        else:
            tag = "Outside"
            base_word = word

        # Record the original form (before replacements) at this position
        # We don't know the final offset yet (replacements may shift it),
        # so we store by word index and resolve offsets after replacements
        stripped_words.append((base_word, tag, base_word))  # (word, tag, original_form)
        current_pos += len(base_word)

    # Second pass: apply replacements to each word individually,
    # then build the final text and record offsets
    replacements = load_replacements("replacements.json")
    final_words = []
    current_pos = 0

    for base_word, tag, original_form in stripped_words:
        replaced_word, _ = apply_replacements_with_mapping(base_word, replacements)
        # Strip leading/trailing punctuation from original_form to match
        # what the tokenizer does when it splits punctuation into separate tokens
        stripped_original = original_form.strip(string.punctuation)
        # Record the offset of this word in the final text
        direct_speech_tags[current_pos] = tag
        original_forms[current_pos] = stripped_original if stripped_original else original_form
        final_words.append(replaced_word)
        current_pos += len(replaced_word)

    text = ''.join(final_words)

    # ------------------------------------------------------------------
    # 9️⃣  Load Spacy model and process
    # ------------------------------------------------------------------
    nlp = spacy.load("de_dep_news_trf")
    nlp.tokenizer = BertTokenizer(nlp.vocab, new_tokenizer)

    @Language.component("attribute_tagging")
    def attribute_tagger(doc):

        replaced_line_lengths = []
        for line in cleaned_lines:
            # Replicate step 8 exactly, word by word
            line_length = 0
            for word in re.split(r'(\s)', line):
                if not word:
                    continue
                # Strip direct speech marker
                if word.startswith(('¿', '%', '€', '$')):
                    base_word = word[1:]
                else:
                    base_word = word
                replaced_word, _ = apply_replacements_with_mapping(base_word, replacements)
                line_length += len(replaced_word)
            replaced_line_lengths.append(line_length)

        char_positions = []
        current_pos = 0
        for length in replaced_line_lengths:
            char_positions.append((current_pos, current_pos + length))
            current_pos += length

        token_offsets = doc._.token_offsets
        use_custom_offsets = token_offsets is not None and len(token_offsets) == len(doc)

        for i, token in enumerate(doc):
            if use_custom_offsets:
                tok_start = token_offsets[i][0]
            else:
                tok_start = token.idx

            token._.direct_speech = direct_speech_tags.get(tok_start)
            token._.original_form = original_forms.get(tok_start)

            for idx, (line_start, line_end) in enumerate(char_positions):
                if line_start <= tok_start < line_end:
                    token._.page_number = page_numbers.get(idx)
                    token._.book_number = book_numbers.get(idx)
                    token._.paragraph_number = paragraph_numbers.get(idx)
                    if not is_at_line[idx]:
                        token._.line_number = line_numbers.get(idx)
                    break

        return doc
        
    nlp.add_pipe("attribute_tagging", before="tagger")
    nlp.add_pipe("transformer", after="BERTtokenizer")
    
    # Process the text with Spacy
    doc = nlp(text)

    # ------------------------------------------------------------------
    # Print tokens with attributes
    # ------------------------------------------------------------------
    for sent in doc.sents:
        for token in sent:
            direct_speech = token._.direct_speech or "N/A"
            line_num = token._.line_number or "N/A"
            paragraph_num = token._.paragraph_number or "N/A"
            book_num = token._.book_number or "N/A"
            page_num = token._.page_number or "N/A"
            original = token._.original_form or token.text  # fall back to token text
            print(f"Token: '{token.text}' | Original: '{original}' | POS: '{token.pos_}' | Line: {line_num} | Paragraph: {paragraph_num} | Page: {page_num} | Book: {book_num} | Direct Speech?: {direct_speech}")

if __name__ == '__main__':
    main()