#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
merge_original_and_analyzed.py

Combine an original TEI‑like XML file (MA.xml) with a token‑by‑token POS‑tagged
XML file (MAtag.xml).  The result keeps the original structural markup
(<div>, <p>, <l>, <lg>, <milestone>, <pb>, …) but replaces every word and the
six punctuation marks (.,;:?! ) with the corresponding <w> or <pc> element from
the analysed file.  All *other* punctuation (quotes, brackets, dashes, …) is
kept verbatim from the original document.

If a mismatch is found the script aborts and prints:
    – the XPath of the element where the mismatch occurred,
    – the last five successful matches (original token → analysed XML).

Usage
-----
    python merge_original_and_analyzed.py MA.xml MAtag.xml merged.xml
"""

import sys
import re
import copy
from pathlib import Path
from lxml import etree

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
# The six punctuation marks that the tagger keeps as separate tokens.
TAGGER_PUNCT = {".", ",", ";", ":", "?", "!"}

# ----------------------------------------------------------------------
# Tokeniser
# ----------------------------------------------------------------------
# 1. any run of whitespace
# 2. a single punctuation character that the tagger keeps
# 3. any single character that is NOT alphanumeric, NOT whitespace and NOT one
#    of the six kept punctuation marks (quotes, brackets, dashes, etc.)
# 4. a run of alphanumeric characters (a word)
TOKEN_RE = re.compile(r"""
    (\s+)                     |   # 1 – whitespace
    ([.,;:?!])                |   # 2 – punctuation kept by the tagger
    ([^\w\s.,;:?!]+)          |   # 3 – other punctuation (quotes, dashes …)
    (\w+)                         # 4 – words (letters, digits, underscore)
    """, re.VERBOSE)


def tokenise(text: str):
    """
    Yield tokens from *text* in exactly the order the tagger would have seen
    them.

    The order of the capture groups in ``TOKEN_RE`` guarantees that every
    character of the input appears in exactly one token:

    * whitespace → returned unchanged (the tagger discards it)
    * one of the six punctuation marks → returned as a single character
    * any other punctuation (e.g. «, », (, ), –) → returned as its own token
    * a word (run of alphanumerics) → returned as a single token
    """
    for ws, kept_punct, other_punct, word in TOKEN_RE.findall(text):
        if ws:
            yield ws
        elif kept_punct:
            yield kept_punct
        elif other_punct:
            yield other_punct
        else:
            yield word


def load_analyzed_tokens(root):
    """Return a flat list of the <w> and <pc> elements from the analysed file."""
    return [el for el in root.iter() if el.tag in ("w", "pc")]


def append_item(parent, item, last):
    """Append *item* (string or Element) after *last* inside *parent*."""
    if isinstance(item, str):
        if last is None:
            parent.text = (parent.text or "") + item
        else:
            last.tail = (last.tail or "") + item
        return last
    else:   # Element
        parent.append(item)
        return item


def process_text(parent, text, token_iter, matches, xpath):
    """
    Replace the plain *text* of *parent* with a mixture of raw strings and
    deep‑copied analysed tokens taken from *token_iter*.

    After the replacement the original *text* is cleared (``parent.text = None``)
    so that the same characters are never processed a second time.
    """
    if text is None:
        return

    items = []          # strings and Elements in the correct order

    for tok in tokenise(text):
        # --------------------------------------------------------------
        # 1. Whitespace – keep it exactly as it appears (the tagger discards it)
        # --------------------------------------------------------------
        if tok.isspace():
            items.append(tok)
            continue

        # --------------------------------------------------------------
        # 2. One of the six punctuation marks that the tagger kept
        # --------------------------------------------------------------
        if tok in TAGGER_PUNCT:
            try:
                analysed = next(token_iter)
            except StopIteration:
                raise RuntimeError(
                    f"Ran out of analysed tokens while expecting a <pc> for "
                    f"punctuation ‘{tok}’ at {xpath}"
                )
            if analysed.tag != "pc" or analysed.text != tok:
                raise RuntimeError(
                    f"Mismatch at {xpath} – expected <pc>{tok}</pc> but got "
                    f"<{analysed.tag}>{analysed.text}</{analysed.tag}>"
                )
            items.append(copy.deepcopy(analysed))
            matches.append((tok, etree.tostring(analysed, encoding="unicode")))
            matches[:] = matches[-5:]
            continue

        # --------------------------------------------------------------
        # 3. “Other” punctuation (quotes, brackets, dashes, …) – keep verbatim
        # --------------------------------------------------------------
        if not any(ch.isalnum() for ch in tok):
            items.append(tok)
            continue

        # --------------------------------------------------------------
        # 4. Word – take the next <w> element (no text comparison needed)
        # --------------------------------------------------------------
        try:
            analysed = next(token_iter)
        except StopIteration:
            raise RuntimeError(
                f"Ran out of analysed tokens while expecting a <w> for "
                f"word ‘{tok}’ at {xpath}"
            )
        if analysed.tag != "w":
            raise RuntimeError(
                f"Mismatch at {xpath} – expected a <w> element for word "
                f"‘{tok}’ but got <{analysed.tag}>"
            )
        items.append(copy.deepcopy(analysed))
        matches.append((tok, etree.tostring(analysed, encoding="unicode")))
        matches[:] = matches[-5:]

    # ------------------------------------------------------------------
    # Append the newly built sequence to *parent*.
    # Existing children (milestones, <pb>, …) are kept – we only add the
    # new <w>/<pc> elements after whatever is already there.
    # ------------------------------------------------------------------
    last = None
    if len(parent):
        last = parent[-1]          # start after the last existing child
    for it in items:
        last = append_item(parent, it, last)

    # Finally, erase the original text so it is not processed again.
    parent.text = None


def walk_and_merge(orig_elem, token_iter, matches):
    """
    Recursively walk *orig_elem* and replace its textual content.

    * The algorithm remembers the original children, removes them, processes
      the element’s own text (creating <w>/<pc> nodes), then re‑inserts the
      original children one‑by‑one, processing each child’s tail immediately
      after the child.  This guarantees that milestones stay exactly where they
      were in the source.
    * Elements that we have just created (`w` or `pc`) are **skipped** – they
      must not be tokenised again.
    """
    # ------------------------------------------------------------------
    # 1. Skip the elements we have inserted ourselves.
    # ------------------------------------------------------------------
    if orig_elem.tag in ("w", "pc"):
        return

    xpath = orig_elem.getroottree().getpath(orig_elem)

    # ------------------------------------------------------------------
    # 2. Remember the original children and wipe the element clean.
    # ------------------------------------------------------------------
    original_children = list(orig_elem)          # copy the list
    for child in original_children:
        orig_elem.remove(child)

    # ------------------------------------------------------------------
    # 3. Process the element's own text (the text that appears before any
    #    child).  This creates the <w>/<pc> nodes that belong to the leading
    #    text of the element.
    # ------------------------------------------------------------------
    process_text(orig_elem, orig_elem.text, token_iter, matches, xpath)

    # ------------------------------------------------------------------
    # 4. Re‑insert the original children in their original order.
    #    After each child we immediately process its tail, which inserts the
    #    tokens that follow the child (e.g. the words after a <milestone>).
    # ------------------------------------------------------------------
    for child in original_children:
        # put the original child back
        orig_elem.append(child)

        # recurse into the child (it may contain its own text, other milestones,
        # etc.).  The recursion will automatically skip any <w>/<pc> that we
        # have just added.
        walk_and_merge(child, token_iter, matches)

        # now handle the tail that follows this child
        process_text(orig_elem, child.tail, token_iter, matches, xpath)
        child.tail = None          # prevent double‑processing


def main(original_path: Path, analysed_path: Path, output_path: Path):
    parser = etree.XMLParser(remove_blank_text=True)
    orig_tree = etree.parse(str(original_path), parser)
    analysed_tree = etree.parse(str(analysed_path), parser)

    analysed_tokens = load_analyzed_tokens(analysed_tree.getroot())
    token_iter = iter(analysed_tokens)

    matches = []
    try:
        walk_and_merge(orig_tree.getroot(), token_iter, matches)
    except RuntimeError as exc:
        sys.stderr.write(f"\nERROR: {exc}\n")
        sys.stderr.write("Last five successful matches (original → analysed):\n")
        for orig, ana in matches:
            sys.stderr.write(f"    {orig!r} → {ana}\n")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Warn if there are leftover analysed tokens (should not happen)
    # ------------------------------------------------------------------
    try:
        next(token_iter)
        sys.stderr.write(
            "\nWARNING: there are still analysed tokens left after processing the "
            "original document.  The output may be incomplete.\n"
        )
    except StopIteration:
        pass

    # ------------------------------------------------------------------
    # Write the merged document
    # ------------------------------------------------------------------
    orig_tree.write(
        str(output_path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True,
    )
    print(f"Successfully written merged file to {output_path}")


# ----------------------------------------------------------------------
# Command‑line interface
# ----------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.stderr.write(
            "Usage: python merge_original_and_analyzed.py "
            "original.xml analysed.xml output.xml\n"
        )
        sys.exit(2)

    original_file = Path(sys.argv[1])
    analysed_file = Path(sys.argv[2])
    output_file = Path(sys.argv[3])

    if not original_file.is_file():
        sys.stderr.write(f"Original file not found: {original_file}\n")
        sys.exit(2)
    if not analysed_file.is_file():
        sys.stderr.write(f"Analysed file not found: {analysed_file}\n")
        sys.exit(2)

    main(original_file, analysed_file, output_file)