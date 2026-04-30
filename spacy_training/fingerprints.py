# fingerprints.py
"""
Builds a fingerprint lookup table from expansions.json and writes
it to fingerprints.json for human review and editing.

A fingerprint is the tuple of subword tokens that the HuggingFace
tokenizer produces for a contraction surface key.

For each entry the file records:
  - original_subwords : what the tokenizer actually produces
                        for the surface form as a whole
  - correct_subwords  : the component words re-tokenized
                        individually and recombined with ##
                        prefixes — always populated, never null
  - analyses          : form/pos/morph/lemma per component word
  - correction_needed : True if original_subwords != correct_subwords

After reviewing fingerprints.json you can:
  - Edit correct_subwords manually for any entry
  - Set correct_subwords to null to disable a correction entirely
  - The pipeline reads from fingerprints.json at runtime

Usage
-----
  python fingerprints.py \
      --expansions  data/expansions.json \
      --tokenizer   BERTtokenizer.json \
      --output      data/fingerprints.json

Or import and call directly:
  from fingerprints import load_fingerprints
"""

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import srsly
from tokenizers import Tokenizer


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def normalise(text: str) -> str:
    """NFC normalisation + lowercase. Used for all key lookups."""
    return unicodedata.normalize("NFC", text).lower()


def strip_special_tokens(tokens: List[str]) -> List[str]:
    """Remove BERT special tokens from a token list."""
    special = {"[CLS]", "[SEP]", "<s>", "</s>", "[PAD]", "[UNK]"}
    return [t for t in tokens if t not in special]


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def tokenize(text: str, tokenizer: Tokenizer) -> List[str]:
    """
    Tokenize a string and return the subword token list,
    with special tokens removed.
    """
    enc = tokenizer.encode(normalise(text))
    return strip_special_tokens(enc.tokens)


def compute_correct_subwords(
    analyses:  List[dict],
    tokenizer: Tokenizer,
) -> List[str]:
    """
    Computes the corrected subword sequence for a contraction by
    re-tokenizing each component word independently and combining
    the results into a single sequence with ## prefixes.

    The result may have a different number of tokens than the
    original WordPiece tokenization of the surface form — this is
    acceptable. The pipeline uses this sequence to override the
    tokenizer's output regardless of length difference.

    Convention:
      - Very first subword of the sequence: no ## prefix
      - All subsequent subwords (any component): ## prefix

    Example
    -------
    components: ["an", "der"]
      "an"  -> ["an"]
      "der" -> ["der"]
    result: ["an", "##der"]

    Example (three-way)
    -------------------
    components: ["vn", "c", "ir"]
      "vn" -> ["vn"]
      "c"  -> ["c"]
      "ir" -> ["ir"]
    result: ["vn", "##c", "##ir"]
    """
    component_forms = [a["form"] for a in analyses]

    component_subwords = []
    for form in component_forms:
        toks = tokenize(form, tokenizer)
        if toks:
            component_subwords.append(toks)
        else:
            component_subwords.append([normalise(form)])

    corrected     = []
    first_overall = True

    for comp_subs in component_subwords:
        for sub in comp_subs:
            stripped = sub.lstrip("#")
            if not stripped:
                continue
            if first_overall:
                corrected.append(stripped)
                first_overall = False
            else:
                corrected.append("##" + stripped)

    return corrected


def build_fingerprint_entries(
    expansions: dict,
    tokenizer:  Tokenizer,
) -> dict:
    """
    Builds the full fingerprint entry dict from expansions.

    Returns a dict keyed by surface form. Each value is a dict with:
      original_subwords : list of str
      correct_subwords  : list of str
      analyses          : list of dicts
      correction_needed : bool
    """
    entries = {}
    skipped = 0

    for surface_key, analyses in expansions.items():

        original_subs = tokenize(surface_key, tokenizer)

        if not original_subs:
            skipped += 1
            continue

        correct_subs      = compute_correct_subwords(analyses, tokenizer)
        correction_needed = (correct_subs != original_subs)

        entries[surface_key] = {
            "original_subwords": original_subs,
            "correct_subwords":  correct_subs,
            "analyses":          analyses,
            "correction_needed": correction_needed,
        }

    if skipped:
        print(f"  Skipped {skipped} entries "
              f"(empty tokenizer output).")

    return entries


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def save_fingerprints(entries: dict, output_path: str) -> None:
    """
    Writes fingerprint entries to a JSON file sorted by surface key.
    Also writes a companion file of entries where correction_needed
    is True, for focused review.
    """
    output_path    = Path(output_path)
    sorted_entries = dict(sorted(entries.items()))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_entries, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(entries)} entries to {output_path}.")

    correction_entries = {
        k: v for k, v in sorted_entries.items()
        if v["correction_needed"]
    }
    if correction_entries:
        companion_path = output_path.with_stem(
            output_path.stem + "_corrections"
        )
        with open(companion_path, "w", encoding="utf-8") as f:
            json.dump(
                correction_entries, f, ensure_ascii=False, indent=2
            )
        print(
            f"Wrote {len(correction_entries)} corrected entries "
            f"to {companion_path}."
        )
    else:
        print("No corrections needed — companion file not written.")


def load_fingerprints_from_file(fingerprints_path: str) -> dict:
    """
    Loads fingerprints.json and converts it to the runtime lookup
    format used by BertTokenizer._override_subword_boundaries().

    Runtime format maps:
      subword_tuple -> {
          "surface":          str,
          "analyses":         list of dicts,
          "correct_subwords": list of str or None,
      }

    Entries where correct_subwords is null (disabled by user)
    are excluded from the runtime lookup.
    """
    with open(fingerprints_path, encoding="utf-8") as f:
        raw = json.load(f)

    fingerprints = {}
    skipped      = 0
    disabled     = 0

    for surface_key, entry in raw.items():
        original_subs = entry.get("original_subwords")
        correct_subs  = entry.get("correct_subwords")
        analyses      = entry.get("analyses", [])

        if not original_subs:
            skipped += 1
            continue

        if correct_subs is None:
            disabled += 1
            continue

        fp = tuple(original_subs)

        if fp not in fingerprints:
            fingerprints[fp] = {
                "surface":          surface_key,
                "analyses":         analyses,
                "correct_subwords": correct_subs,
            }

    if skipped:
        print(f"  load_fingerprints: skipped {skipped} entries "
              f"(empty original_subwords).")
    if disabled:
        print(f"  load_fingerprints: skipped {disabled} entries "
              f"(correct_subwords set to null by user).")

    return fingerprints


def load_fingerprints(fingerprints_path: str) -> dict:
    """
    Load a reviewed fingerprints.json and return the runtime
    lookup dict. Use this in main_script.py and json_to_spacy.py.
    """
    print(f"Loading fingerprints from {fingerprints_path} ...")
    fingerprints = load_fingerprints_from_file(fingerprints_path)
    print(f"  Loaded {len(fingerprints)} runtime fingerprints.")
    return fingerprints


def build_and_save_fingerprints(
    expansions_path: str,
    tokenizer_path:  str,
    output_path:     str,
) -> dict:
    """
    Convenience function: load expansions, build fingerprints,
    save to file, return runtime lookup dict.
    """
    print(f"Loading expansions from {expansions_path} ...")
    expansions = srsly.read_json(expansions_path)
    print(f"  Loaded {len(expansions)} expansion entries.")

    print(f"Loading tokenizer from {tokenizer_path} ...")
    tokenizer = Tokenizer.from_file(tokenizer_path)

    print("Building fingerprint entries ...")
    entries = build_fingerprint_entries(expansions, tokenizer)
    print(f"  Built {len(entries)} entries.")

    print(f"Saving to {output_path} ...")
    save_fingerprints(entries, output_path)

    print("Converting to runtime lookup format ...")
    fingerprints = load_fingerprints_from_file(output_path)
    print(f"  Runtime lookup has {len(fingerprints)} entries.")

    return fingerprints


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(entries: dict) -> None:
    total            = len(entries)
    needs_correction = sum(
        1 for e in entries.values() if e["correction_needed"]
    )
    no_change        = total - needs_correction
    print(f"\n── Fingerprint Summary ──────────────────────────────")
    print(f"  Total entries:               {total}")
    print(f"  No correction needed:        {no_change}")
    print(f"  Correction will be applied:  {needs_correction}")
    print(f"────────────────────────────────────────────────────\n")


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build fingerprints.json from expansions.json. "
            "Review and optionally edit the output before "
            "running the pipeline."
        )
    )
    parser.add_argument(
        "--expansions",
        default="data/expansions.json",
        help="Path to expansions.json"
    )
    parser.add_argument(
        "--tokenizer",
        default="BERTtokenizer.json",
        help="Path to BERTtokenizer.json"
    )
    parser.add_argument(
        "--output",
        default="data/fingerprints.json",
        help="Path to write fingerprints.json"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a summary after building"
    )
    args = parser.parse_args()

    print(f"Loading expansions from {args.expansions} ...")
    expansions = srsly.read_json(args.expansions)
    print(f"  Loaded {len(expansions)} expansion entries.")

    print(f"Loading tokenizer from {args.tokenizer} ...")
    tokenizer = Tokenizer.from_file(args.tokenizer)

    print("Building fingerprint entries ...")
    entries = build_fingerprint_entries(expansions, tokenizer)
    print(f"  Built {len(entries)} entries.")

    print(f"Saving to {args.output} ...")
    save_fingerprints(entries, args.output)

    if args.summary:
        print_summary(entries)

    print("\nDone.")
    print(
        f"Review {args.output} and edit correct_subwords as needed.\n"
        f"Set correct_subwords to null to disable any entry."
    )


if __name__ == "__main__":
    main()