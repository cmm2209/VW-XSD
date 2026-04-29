# mwt_component.py
import unicodedata
import srsly
import spacy
from spacy.language import Language
from spacy.tokens import Doc, Token, Span

# ---------------------------------------------------------------------------
# Token extensions
# ---------------------------------------------------------------------------
Token.set_extension("is_contraction_boundary", default=False, force=True)
Token.set_extension("line_number",             default=None,  force=True)
Token.set_extension("page_number",             default=None,  force=True)
Token.set_extension("paragraph_number",        default=None,  force=True)
Token.set_extension("book_number",             default=None,  force=True)
Token.set_extension("direct_speech",           default=None,  force=True)
Token.set_extension("original_form",           default=None,  force=True)

# ---------------------------------------------------------------------------
# Span extensions for MWT syntactic words
# ---------------------------------------------------------------------------
Span.set_extension("word_form",         default=None, force=True)
Span.set_extension("word_pos",          default=None, force=True)
Span.set_extension("word_morph",        default=None, force=True)
Span.set_extension("word_lemma",        default=None, force=True)
Span.set_extension("word_index",        default=None, force=True)
Span.set_extension("surface_token_idx", default=None, force=True)


# ---------------------------------------------------------------------------
# MWT Detector
# ---------------------------------------------------------------------------

@Language.factory("mwt_detector")
def create_mwt_detector(nlp, name):
    return MWTDetector(nlp.vocab)


class MWTDetector:
    """
    Uses GHisBERT contextual embeddings to decide, per ## token,
    whether it marks a genuine contraction boundary (True)
    or is normal subword tokenization (False).

    Sets token._.is_contraction_boundary on each ## token.
    """

    def __init__(self, vocab):
        self.vocab = vocab

    def __call__(self, doc):
        trf_data = doc._.trf_data
        if trf_data is None:
            return doc

        for i, token in enumerate(doc):
            if token.text.startswith("##"):
                vec = self._get_boundary_vector(trf_data, i)
                token._.is_contraction_boundary = self._classify(vec)

        return doc

    def _get_boundary_vector(self, trf_data, token_idx):
        last_layer = trf_data.tensors[-1][0]
        if token_idx > 0:
            vec = (last_layer[token_idx - 1] + last_layer[token_idx]) / 2
        else:
            vec = last_layer[token_idx]
        return vec

    def _classify(self, vector):
        raise NotImplementedError("Load trained weights via from_disk()")

    def to_disk(self, path, exclude=()):
        srsly.write_json(path / "cfg.json", {})

    def from_disk(self, path, exclude=()):
        return self


# ---------------------------------------------------------------------------
# MWT Annotator
# ---------------------------------------------------------------------------

@Language.factory("mwt_annotator")
def create_mwt_annotator(nlp, name):
    return MWTAnnotator(nlp.vocab)


class MWTAnnotator:
    """
    Processes MWT contractions without modifying the token stream.

    For each contraction (a surface token followed by one or more
    ## tokens where is_contraction_boundary is True):
      - Reconstructs the surface form from the root token and its
        ## pieces
      - Looks up the expansion table to get per-word analyses
      - Creates Span entries in doc.spans["mwt_words"] for each
        syntactic word, carrying form/pos/morph/lemma annotations

    The subword token stream is left completely intact because:
      - The transformer and TransformerListeners need the subword
        tokens to align their inputs correctly
      - ## prefixes are useful structural signals for the tagger
      - No downstream component requires a merged stream given
        that syntactic word annotations live in
        doc.spans["mwt_words"]

    Non-contraction ## tokens are ignored.
    """

    def __init__(self, vocab, expansions=None):
        self.vocab      = vocab
        self.expansions = expansions or {}

    def __call__(self, doc):
        mwt_spans = []

        i = 0
        while i < len(doc):
            token = doc[i]

            j               = i + 1
            subword_indices = []
            while j < len(doc) and doc[j].text.startswith("##"):
                subword_indices.append(j)
                j += 1

            if subword_indices:
                is_contraction = any(
                    doc[k]._.is_contraction_boundary
                    for k in subword_indices
                )

                if is_contraction:
                    surface = token.text + "".join(
                        doc[k].text.lstrip("#")
                        for k in subword_indices
                    )
                    lower = unicodedata.normalize(
                        "NFC", surface.lower()
                    )

                    if lower in self.expansions:
                        analyses = self.expansions[lower]
                        for word_idx, analysis in enumerate(analyses):
                            span = doc[token.i : token.i + 1]
                            span._.word_form         = analysis.get(
                                "form",  ""
                            )
                            span._.word_pos          = analysis.get(
                                "pos",   "X"
                            )
                            span._.word_morph        = analysis.get(
                                "morph", ""
                            )
                            span._.word_lemma        = analysis.get(
                                "lemma", ""
                            )
                            span._.word_index        = word_idx
                            span._.surface_token_idx = token.i
                            mwt_spans.append(span)

                i = j
            else:
                i += 1

        doc.spans["mwt_words"] = spacy.tokens.SpanGroup(
            doc,
            name  = "mwt_words",
            spans = mwt_spans,
        )

        return doc

    def to_disk(self, path, exclude=()):
        srsly.write_json(path / "expansions.json", self.expansions)

    def from_disk(self, path, exclude=()):
        self.expansions = srsly.read_json(path / "expansions.json")
        return self