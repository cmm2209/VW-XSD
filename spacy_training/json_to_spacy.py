# json_to_spacy.py
import json
import glob
import random
import unicodedata
import srsly
import sys
from pathlib import Path
from collections import Counter
from spacy.tokens import DocBin, Doc, Token, Span
import spacy

from text_replacements import load_replacements, apply_replacements_with_mapping

Token.set_extension("is_contraction_boundary", default=False, force=True)
Token.set_extension("sent_type",               default=None,  force=True)
Span.set_extension("sent_type",                default=None,  force=True)
Span.set_extension("word_form",                default=None,  force=True)
Span.set_extension("word_pos",                 default=None,  force=True)
Span.set_extension("word_morph",               default=None,  force=True)
Span.set_extension("word_lemma",               default=None,  force=True)
Span.set_extension("word_index",               default=None,  force=True)
Span.set_extension("surface_token_idx",        default=None,  force=True)

SENT_TYPES = {"DE", "IE", "EE", "QE"}

# Minimum number of times a contraction surface form must appear
# across the corpus to be included in the expansion table.
MIN_CONTRACTION_FREQ = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def group_tokens_by_virttok(tokens):
    groups = {}
    order  = []
    for tok in tokens:
        vt = tok["virttok"]
        if vt not in groups:
            groups[vt] = []
            order.append(vt)
        groups[vt].append(tok)
    return order, groups


def is_punct_token(tok):
    """
    Returns True if this token should be excluded from all join
    calculations (surface key construction, analyses building,
    norm pair assembly).  Currently excludes any token whose
    pos_upos is "PUNCT".
    """
    return tok.get("pos_upos", "") == "PUNCT"


def is_contraction_group(group):
    """
    Quick pre-filter: returns True if any token in the group
    has a 'join' field at all. Full validation (join directions,
    PUNCT tokens, minimum length, minimum valid forms) is
    handled by is_valid_contraction() on the sorted group.
    """
    return any("join" in t for t in group)


def is_valid_field(value):
    """
    Returns True if a form or norm field value is non-empty
    and contains at least one non-whitespace character.
    """
    return bool(value and value.strip())


def is_valid_contraction(sorted_group):
    """
    Returns False if the group should NOT be treated as a
    genuine MWT contraction, for any of the following reasons:

    - Fewer than two tokens total
    - After removing PUNCT tokens, fewer than two tokens remain
      (a group that consists of only one content token plus
      punctuation is not a genuine morphological contraction)
    - After removing PUNCT tokens, fewer than two tokens have
      non-empty form fields
    - After removing PUNCT tokens, there is not at least one
      join=right/both AND one join=left/both token
    - The final *non-PUNCT* token (i.e. the last token of the
      content part) has pos_upos = "PUNCT" — this guard is now
      redundant given the filtering above but is kept for safety

    All join-direction and form-count checks operate exclusively
    on the non-PUNCT subset so that attached punctuation cannot
    masquerade as a contraction component.
    """
    if len(sorted_group) < 2:
        return False

    # All join-related checks are performed on the non-PUNCT subset
    non_punct = [t for t in sorted_group if not is_punct_token(t)]

    if len(non_punct) < 2:
        return False

    # At least two non-PUNCT tokens must have non-empty form fields
    tokens_with_forms = [
        t for t in non_punct
        if is_valid_field(t.get("form", ""))
    ]
    if len(tokens_with_forms) < 2:
        return False

    has_right = any(
        t.get("join") in ("right", "both") for t in non_punct
    )
    has_left  = any(
        t.get("join") in ("left",  "both") for t in non_punct
    )
    if not (has_right and has_left):
        return False

    # Safety check: final non-PUNCT token must not itself be PUNCT
    # (should be unreachable after the filter above, but kept for
    # defensive correctness)
    final_pos = non_punct[-1].get("pos_upos", "")
    if final_pos == "PUNCT":
        return False

    return True


def get_surface_form(virttok_id, token_dipl_list):
    for td in token_dipl_list:
        if td["virttok"] == virttok_id:
            form = td.get("form", "")
            return form if form and form.strip() else None
    return None


def sort_group(group):
    order_map = {"MS1": 0, "MS2": 1, "MS3": 2}
    return sorted(
        group,
        key=lambda t: order_map.get(t.get("token_type", "MS1"), 0)
    )


def apply_replacements(text, replacements):
    replaced, _ = apply_replacements_with_mapping(text, replacements)
    return replaced


def nfc(text):
    """
    NFC normalisation only — preserves case.
    Applied BEFORE replacements so replacement rules see a
    consistent Unicode form. Case preserved for tagger training.
    """
    return unicodedata.normalize("NFC", text)


def normalise(text):
    """
    NFC normalisation + lowercase.
    Used for expansion table lookup keys only — never for
    word forms stored in training docs.
    Applied BEFORE replacements.
    """
    return unicodedata.normalize("NFC", text).lower()


def get_raw(tok, use_norm):
    """
    Returns the appropriate raw string for a token given whether
    we are using norm or form values.

    For norm variant: uses "norm" field if present and non-empty,
    otherwise falls back to "form" field.
    For form variant: uses "form" field directly.

    Returns None if the selected field is empty or absent,
    so the caller can skip this token.
    """
    if use_norm:
        norm = tok.get("norm", "")
        if is_valid_field(norm):
            return norm
        form = tok.get("form", "")
        return form if is_valid_field(form) else None
    else:
        form = tok.get("form", "")
        return form if is_valid_field(form) else None


# ---------------------------------------------------------------------------
# Build expansion dictionary
# ---------------------------------------------------------------------------

def make_analyses(parts_iter, replacements):
    """
    Build a list of analysis dicts from an iterable of
    (tok, raw_form) pairs.
    Each dict has keys: form, pos, morph, lemma.
    nfc() applied BEFORE replacements.
    Tokens with empty or blank form fields are skipped.
    PUNCT tokens are excluded by the caller before reaching here.
    """
    analyses = []
    for tok, raw_form in parts_iter:

        if not is_valid_field(raw_form):
            continue

        feats     = tok.get("feats_ud", {})
        morph_str = "|".join(
            f"{k}={v}" for k, v in sorted(feats.items())
        ) if feats else ""

        replaced_form = apply_replacements(nfc(raw_form), replacements)

        if not replaced_form:
            replaced_form = nfc(raw_form) if nfc(raw_form) else "□"

        analyses.append({
            "form":  replaced_form,
            "pos":   tok.get("pos_upos", "X"),
            "morph": morph_str,
            "lemma": tok.get("lemma", raw_form),
        })
    return analyses


def _non_punct_norm_pairs(sorted_group):
    """
    Build the list of (tok, raw_string) pairs for the norm-surface
    key, excluding any token whose pos_upos is "PUNCT".

    For each non-PUNCT token: use "norm" if non-empty, else "form".
    Returns a list of (tok, str) pairs; entries with no usable
    string are omitted.
    """
    pairs = []
    for t in sorted_group:
        if is_punct_token(t):
            continue
        norm = t.get("norm", "")
        if is_valid_field(norm):
            pairs.append((t, norm))
        else:
            form = t.get("form", "")
            if is_valid_field(form):
                pairs.append((t, form))
    return pairs


def count_contraction_frequencies(json_files, replacements):
    """
    First pass: count how many times each candidate contraction
    surface key appears across all files.

    Returns a Counter mapping normalised surface key → frequency.

    Both the form-surface key and the norm-surface key are counted
    independently, since either may appear at inference time.

    PUNCT tokens are excluded from norm-surface key construction.
    """
    freq = Counter()

    for file_idx, path in enumerate(json_files):
        print(
            f"Counting contractions: {file_idx + 1}/{len(json_files)}",
            end="\r", flush=True
        )

        data       = load_json_file(path)
        tokens     = data["token"]
        token_dipl = data.get("token_dipl", [])

        order, groups = group_tokens_by_virttok(tokens)

        for vt_id in order:
            group = groups[vt_id]

            if not is_contraction_group(group):
                continue

            sorted_group = sort_group(group)

            if not is_valid_contraction(sorted_group):
                continue

            # Count form-surface key (uses the diplomatic surface
            # form from token_dipl — no per-token PUNCT filtering
            # needed here as it is a single surface string)
            surface_raw = get_surface_form(vt_id, token_dipl)
            key_orig    = None
            if surface_raw is not None:
                key_orig = apply_replacements(
                    normalise(surface_raw), replacements
                )
                if not key_orig:
                    key_orig = normalise(surface_raw)
                if key_orig:
                    freq[key_orig] += 1

            # Count norm-surface key — PUNCT tokens excluded
            norm_pairs = _non_punct_norm_pairs(sorted_group)

            if norm_pairs:
                norm_surface = "".join(pair[1] for pair in norm_pairs)
                key_norm     = apply_replacements(
                    normalise(norm_surface), replacements
                )
                if not key_norm:
                    key_norm = normalise(norm_surface)
                if key_norm and key_norm != key_orig:
                    freq[key_norm] += 1

    print()
    return freq


def build_expansions_from_json(json_files, replacements,
                               freq, min_freq=MIN_CONTRACTION_FREQ):
    """
    Second pass: build expansion dictionary from all JSON files,
    only including entries whose surface key appears at least
    min_freq times in the corpus (as counted by
    count_contraction_frequencies()).

    For each qualifying contraction, creates TWO entries:
      1. apply_replacements(normalise(form surface)) → form analyses
      2. apply_replacements(normalise(norm surface)) → norm analyses

    normalise() (NFC + lowercase) is applied BEFORE replacements
    so that replacement rules see a consistent Unicode form.

    PUNCT tokens are excluded from all join calculations (form
    parts, norm pairs, analyses construction).

    Groups are excluded if:
      - Their surface key appears fewer than min_freq times
      - They lack both join=right/both and join=left/both tokens
        among non-PUNCT tokens
      - Fewer than two non-PUNCT tokens have non-empty form fields
      - Any token with pos_upos = "PUNCT" is present in the group
        (handled by excluding such tokens from analysis, not by
        rejecting the whole group)
      - They have no surface form in token_dipl
      - The resulting analyses list has fewer than two entries
    """
    expansions = {}

    for file_idx, path in enumerate(json_files):
        print(
            f"Building expansions: {file_idx + 1}/{len(json_files)}",
            end="\r", flush=True
        )

        data       = load_json_file(path)
        tokens     = data["token"]
        token_dipl = data.get("token_dipl", [])

        order, groups = group_tokens_by_virttok(tokens)

        for vt_id in order:
            group = groups[vt_id]

            if not is_contraction_group(group):
                continue

            sorted_group = sort_group(group)

            if not is_valid_contraction(sorted_group):
                continue

            surface_raw = get_surface_form(vt_id, token_dipl)
            if surface_raw is None:
                continue

            # ── Entry 1: form surface → form analyses ─────────────────
            key_orig = apply_replacements(
                normalise(surface_raw), replacements
            )
            if not key_orig:
                key_orig = normalise(surface_raw)

            # Skip if this key does not meet the frequency threshold
            if freq.get(key_orig, 0) <= min_freq:
                continue

            # Exclude PUNCT tokens from form parts
            form_parts = [
                (t, t["form"])
                for t in sorted_group
                if not is_punct_token(t)
                and is_valid_field(t.get("form", ""))
            ]
            analyses_1 = make_analyses(form_parts, replacements)

            if len(analyses_1) < 2:
                continue

            if key_orig not in expansions:
                expansions[key_orig] = analyses_1

            # ── Entry 2: norm surface → norm analyses ──────────────────
            # Exclude PUNCT tokens from norm pairs
            norm_pairs = _non_punct_norm_pairs(sorted_group)

            if not norm_pairs:
                continue

            norm_surface = "".join(pair[1] for pair in norm_pairs)
            key_norm     = apply_replacements(
                normalise(norm_surface), replacements
            )
            if not key_norm:
                key_norm = normalise(norm_surface)

            # Skip norm key if it does not meet the frequency threshold
            if freq.get(key_norm, 0) <= min_freq:
                continue

            analyses_2 = make_analyses(norm_pairs, replacements)

            if len(analyses_2) < 2:
                continue

            if (key_norm not in expansions
                    and key_norm != key_orig):
                expansions[key_norm] = analyses_2

    print()
    return expansions


# ---------------------------------------------------------------------------
# Build sentence type maps
# ---------------------------------------------------------------------------

def build_sent_type_map(sentences):
    """
    Returns two dicts keyed by 1-based virtual token index:
      sent_start_type[i] = type for sentence beginning at token i
      sent_end_type[i]   = type for sentence ending at token i

    Only DE, IE, EE, QE types are recorded.
    S* and all other values are ignored.
    """
    sent_start_type = {}
    sent_end_type   = {}
    for sent in sentences:
        stype = sent.get("type", "")
        if stype not in SENT_TYPES:
            continue
        sent_start_type[sent["begin"]] = stype
        sent_end_type[sent["end"]]     = stype
    return sent_start_type, sent_end_type


# ---------------------------------------------------------------------------
# Convert JSON documents to spaCy Docs
# ---------------------------------------------------------------------------

def json_to_spacy_docs(json_files, nlp, replacements):
    """
    Convert JSON files to spaCy Doc objects.

    For each source document produces TWO docs:
      1. Using original 'form' values
      2. Using normalised 'norm' values (falling back to 'form'
         if 'norm' is empty or absent)

    Order of operations for word forms:
      nfc() first (NFC only, preserves case) → apply_replacements()

    Tokens with empty or blank form/norm fields are skipped.
    Contraction groups that fail is_valid_contraction() are not
    treated as MWT contractions.
    PUNCT tokens are excluded from all join/MWT span calculations.
    Subword token stream left intact throughout.
    S* punc tags ignored for sentence typing.
    """
    docs = []

    for file_idx, path in enumerate(json_files):
        print(
            f"Converting docs: {file_idx + 1}/{len(json_files)}",
            end="\r", flush=True
        )

        data      = load_json_file(path)
        tokens    = data["token"]
        sentences = data.get("sentence", [])

        order, groups = group_tokens_by_virttok(tokens)

        virttok_to_pos = {
            vt: i + 1 for i, vt in enumerate(order)
        }
        sent_start_type, sent_end_type = build_sent_type_map(sentences)

        token_punc = {}
        for tok in tokens:
            punc = tok.get("punc", "")
            if punc in SENT_TYPES:
                token_punc[tok["virttok"]] = punc

        for use_norm in (False, True):

            words                   = []
            spaces                  = []
            pos_tags                = []
            morph_feats             = []
            is_contraction_boundary = []
            token_positions         = []
            word_punc               = []

            for i, vt_id in enumerate(order):
                group          = groups[vt_id]
                is_contraction = is_contraction_group(group)
                sorted_group   = sort_group(group) if is_contraction \
                                 else group

                # Apply full contraction validation
                if is_contraction and not is_valid_contraction(sorted_group):
                    is_contraction = False

                for j, tok in enumerate(sorted_group):

                    raw = get_raw(tok, use_norm)
                    if raw is None:
                        continue

                    nfc_raw = nfc(raw)
                    word    = apply_replacements(nfc_raw, replacements)

                    if not word:
                        word = nfc_raw if nfc_raw else "□"

                    words.append(word)
                    pos_tags.append(tok.get("pos_upos", "X"))
                    morph_feats.append(tok.get("feats_ud", {}))
                    token_positions.append(vt_id)

                    token_type  = tok.get("token_type", "")
                    is_boundary = (
                        is_contraction and token_type in ("MS2", "MS3")
                    )
                    is_contraction_boundary.append(is_boundary)

                    if j == len(sorted_group) - 1:
                        punc = tok.get("punc", "")
                        word_punc.append(
                            punc if punc in SENT_TYPES else ""
                        )
                    else:
                        word_punc.append("")

                    if j < len(sorted_group) - 1:
                        spaces.append(False)
                    elif i < len(order) - 1:
                        spaces.append(True)
                    else:
                        spaces.append(False)

            if not words:
                continue

            doc = Doc(nlp.vocab, words=words, spaces=spaces)

            # ── Per-token attributes ───────────────────────────────────
            for token, pos, feats, is_boundary in zip(
                doc, pos_tags, morph_feats, is_contraction_boundary
            ):
                token.pos_                      = pos
                token._.is_contraction_boundary = is_boundary
                if feats:
                    morph_str = "|".join(
                        f"{k}={v}" for k, v in sorted(feats.items())
                    )
                    token.set_morph(morph_str)

            # ── Sentence boundaries ────────────────────────────────────
            virttok_to_word_idx = {}
            for word_idx, vt_id in enumerate(token_positions):
                if vt_id not in virttok_to_word_idx:
                    virttok_to_word_idx[vt_id] = word_idx

            sent_start_word_idxs = set()
            if sentences:
                for sent in sentences:
                    begin_vtok = f"t{sent['begin']}"
                    if begin_vtok in virttok_to_word_idx:
                        sent_start_word_idxs.add(
                            virttok_to_word_idx[begin_vtok]
                        )

            for i, token in enumerate(doc):
                token.is_sent_start = (i in sent_start_word_idxs)

            # ── Sentence type labels ───────────────────────────────────
            word_idx_to_sent_end_type = {}
            for word_idx, vt_id in enumerate(token_positions):
                pos_1based = virttok_to_pos.get(vt_id)
                if pos_1based in sent_end_type:
                    word_idx_to_sent_end_type[word_idx] = \
                        sent_end_type[pos_1based]

            for word_idx, punc in enumerate(word_punc):
                if (punc in SENT_TYPES
                        and word_idx not in word_idx_to_sent_end_type):
                    word_idx_to_sent_end_type[word_idx] = punc

            for word_idx, stype in word_idx_to_sent_end_type.items():
                doc[word_idx]._.sent_type = stype

            for sent in doc.sents:
                for tok in reversed(list(sent)):
                    if tok._.sent_type is not None:
                        sent._.sent_type = tok._.sent_type
                        break

            # ── MWT word spans ─────────────────────────────────────────
            mwt_spans = []
            word_idx  = 0

            for vt_id in order:
                group          = groups[vt_id]
                is_contraction = is_contraction_group(group)
                sorted_group   = sort_group(group) if is_contraction \
                                 else group

                # Apply full contraction validation
                if is_contraction and not is_valid_contraction(sorted_group):
                    is_contraction = False

                if is_contraction and word_idx < len(doc):
                    token = doc[word_idx]

                    # Exclude PUNCT tokens from norm pairs for MWT spans
                    norm_pairs = _non_punct_norm_pairs(sorted_group)

                    if norm_pairs:
                        if use_norm:
                            parts = norm_pairs
                        else:
                            # Exclude PUNCT tokens from form parts too
                            parts = [
                                (t, t["form"])
                                for t in sorted_group
                                if not is_punct_token(t)
                                and is_valid_field(t.get("form", ""))
                            ]
                        analyses = make_analyses(parts, replacements)

                        # Only create MWT spans if at least two
                        # analyses were produced
                        if len(analyses) >= 2:
                            for analysis_idx, analysis in enumerate(
                                analyses
                            ):
                                span = doc[token.i : token.i + 1]
                                span._.word_form         = analysis["form"]
                                span._.word_pos          = analysis["pos"]
                                span._.word_morph        = analysis["morph"]
                                span._.word_lemma        = analysis["lemma"]
                                span._.word_index        = analysis_idx
                                span._.surface_token_idx = token.i
                                mwt_spans.append(span)

                # Advance word_idx by the number of tokens in this
                # group that were actually added to words[]
                for tok in sorted_group:
                    if get_raw(tok, use_norm) is not None:
                        word_idx += 1

            doc.spans["mwt_words"] = spacy.tokens.SpanGroup(
                doc,
                name  = "mwt_words",
                spans = mwt_spans,
            )

            docs.append(doc)

    print()
    return docs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    json_dir   = sys.argv[1] if len(sys.argv) > 1 else "."
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    json_files = sorted(glob.glob(f"{json_dir}/*.json"))
    print(f"Found {len(json_files)} JSON files.")

    if not json_files:
        print("No JSON files found. Check your path.")
        sys.exit(1)

    replacements = load_replacements("replacements.json")
    print("Loaded replacements.json.")

    # First pass: count contraction frequencies
    freq = count_contraction_frequencies(json_files, replacements)
    print(
        f"Found {len(freq)} distinct contraction surface keys "
        f"before frequency filtering."
    )

    # Second pass: build expansion table with frequency filter
    expansions = build_expansions_from_json(
        json_files, replacements, freq, min_freq=MIN_CONTRACTION_FREQ
    )
    srsly.write_json(output_dir / "expansions.json", expansions)
    print(
        f"Built expansion table with {len(expansions)} entries "
        f"(minimum frequency: {MIN_CONTRACTION_FREQ})."
    )

    nlp  = spacy.blank("de")
    docs = json_to_spacy_docs(json_files, nlp, replacements)
    print(
        f"Converted {len(docs)} documents "
        f"({len(json_files)} source files × 2 variants)."
    )

    if not docs:
        print("No documents converted. Check JSON structure.")
        sys.exit(1)

    # Shuffle in pairs so form and norm variants of the same
    # source document always end up in the same split
    paired      = list(zip(docs[0::2], docs[1::2]))
    random.seed(42)
    random.shuffle(paired)
    split       = int(len(paired) * 0.9)
    train_pairs = paired[:split]
    dev_pairs   = paired[split:]

    train_docs = [d for pair in train_pairs for d in pair]
    dev_docs   = [d for pair in dev_pairs   for d in pair]

    train_db = DocBin(docs=train_docs, store_user_data=True)
    dev_db   = DocBin(docs=dev_docs,   store_user_data=True)
    train_db.to_disk(output_dir / "train.spacy")
    dev_db.to_disk(output_dir   / "dev.spacy")

    print(
        f"Saved {len(train_docs)} train docs "
        f"and {len(dev_docs)} dev docs."
    )
    print("Done. Files written to data/")


if __name__ == "__main__":
    main()