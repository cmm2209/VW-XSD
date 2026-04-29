# senter_model.py
"""
PyTorch implementation of ConcatPOSMorphTagger.v1

Architecture per token:
  transformer embedding  (from GHisBERT via TransformerListener)
  POS tag embedding      (nn.Embedding, learned)
  morph feature vector   (binary → Linear → ReLU, learned)
       ↓ concatenate
  MLP: Linear → ReLU → Linear → output

Used by both senter and sent_type_detector in Stage C.
The tagger and morphologizer are frozen in Stage C so that
token.pos_ and token.morph_ are stable symbolic inputs.
The POS and morph embedding tables therefore train against
stable inputs and converge reliably.

Registered as:
  @architectures = "custom.ConcatPOSMorphTagger.v1"
"""

from typing import List, Optional, Tuple
from pathlib import Path
import numpy

import torch
import torch.nn as nn

import spacy
from spacy.tokens import Doc
from thinc.api import (
    Model,
    registry,
    get_current_ops,
    torch2xp,
    xp2torch,
)
from thinc.types import Floats2d


# ---------------------------------------------------------------------------
# Feature extraction helpers (run outside the PyTorch graph)
# ---------------------------------------------------------------------------

def extract_pos_ids(docs: List[Doc]) -> torch.Tensor:
    """
    Returns a LongTensor of shape (n_tokens,) containing the
    spaCy integer POS id for each token across all docs.
    """
    ids = [token.pos for doc in docs for token in doc]
    return torch.tensor(ids, dtype=torch.long)


def extract_morph_matrix(
    docs: List[Doc], n_rows: int
) -> torch.Tensor:
    """
    Returns a FloatTensor of shape (n_tokens, n_rows).
    Each row is a binary vector with 1.0 at the hashed index
    of each active morphological feature=value pair.
    Feature strings are hashed into [0, n_rows).
    """
    n_toks = sum(len(doc) for doc in docs)
    mat    = torch.zeros(n_toks, n_rows, dtype=torch.float32)
    row    = 0
    for doc in docs:
        for token in doc:
            for field, values in token.morph.to_dict().items():
                vals = values if isinstance(values, list) else [values]
                for value in vals:
                    col = int(hash(f"{field}_{value}") % n_rows)
                    mat[row, col] = 1.0
            row += 1
    return mat


# ---------------------------------------------------------------------------
# PyTorch nn.Module
# ---------------------------------------------------------------------------

class ConcatPOSMorphModule(nn.Module):
    """
    Combines transformer embeddings with POS and morphology
    features, then passes through a two-layer MLP.

    Parameters
    ----------
    trf_width    : int   Width of transformer (GHisBERT) embeddings
    pos_vocab    : int   Number of distinct POS ids (64 covers all UPOS)
    pos_width    : int   POS embedding size
    morph_vocab  : int   Hash space for morphological feature strings
    morph_width  : int   Projected morphology embedding size
    hidden_width : int   MLP hidden layer width
    nO           : int   Output size (number of labels)
    """

    def __init__(
        self,
        trf_width:    int,
        pos_vocab:    int = 64,
        pos_width:    int = 32,
        morph_vocab:  int = 2048,
        morph_width:  int = 64,
        hidden_width: int = 128,
        nO:           int = 2,
    ):
        super().__init__()

        # POS embedding table
        self.pos_embed  = nn.Embedding(pos_vocab, pos_width)

        # Morphological feature projection
        self.morph_proj = nn.Sequential(
            nn.Linear(morph_vocab, morph_width),
            nn.ReLU(),
        )

        # MLP operating on the concatenated vector
        concat_width = trf_width + pos_width + morph_width
        self.mlp = nn.Sequential(
            nn.Linear(concat_width, hidden_width),
            nn.ReLU(),
            nn.Linear(hidden_width, nO),
        )

        # Xavier initialisation
        nn.init.xavier_uniform_(self.pos_embed.weight)
        nn.init.xavier_uniform_(self.morph_proj[0].weight)
        nn.init.zeros_(self.morph_proj[0].bias)
        nn.init.xavier_uniform_(self.mlp[0].weight)
        nn.init.zeros_(self.mlp[0].bias)
        nn.init.xavier_uniform_(self.mlp[2].weight)
        nn.init.zeros_(self.mlp[2].bias)

    def forward(
        self,
        trf_vecs:  torch.Tensor,   # (n_tokens, trf_width)
        pos_ids:   torch.Tensor,   # (n_tokens,)
        morph_mat: torch.Tensor,   # (n_tokens, morph_vocab)
    ) -> torch.Tensor:             # (n_tokens, nO)

        pos_vecs   = self.pos_embed(pos_ids)        # (n, pos_width)
        morph_vecs = self.morph_proj(morph_mat)     # (n, morph_width)
        combined   = torch.cat(
            [trf_vecs, pos_vecs, morph_vecs], dim=-1
        )
        return self.mlp(combined)


# ---------------------------------------------------------------------------
# Thinc Model wrapper
# ---------------------------------------------------------------------------

@registry.architectures("custom.ConcatPOSMorphTagger.v1")
def build_concat_pos_morph_tagger(
    tok2vec:      Model,
    pos_width:    int = 32,
    morph_width:  int = 64,
    hidden_width: int = 128,
    nO:           Optional[int] = None,
) -> Model[List[Doc], Floats2d]:
    """
    Thinc Model wrapping ConcatPOSMorphModule.

    Input:  List[Doc]  — tokens must have .pos and .morph set
                         (requires tagger + morphologizer upstream)
    Output: Floats2d   — (n_tokens, nO)

    Parameters
    ----------
    tok2vec      : TransformerListener model
    pos_width    : POS embedding dimensionality
    morph_width  : Morphological feature projection dimensionality
    hidden_width : MLP hidden layer width
    nO           : Output size; inferred from label count if None
    """

    def forward(
        model: Model, docs: List[Doc], is_train: bool
    ) -> Tuple[Floats2d, callable]:

        ops = model.ops

        # ── 1. Transformer embeddings ──────────────────────────────────
        trf_out, trf_bp = model.get_ref("tok2vec")(docs, is_train)

        # ── 2. Extract symbolic features ──────────────────────────────
        morph_vocab = model.attrs["morph_vocab"]
        pos_ids     = extract_pos_ids(docs)
        morph_mat   = extract_morph_matrix(docs, morph_vocab)

        # ── 3. Move to correct device ──────────────────────────────────
        m      = model.attrs["torch_model"]
        device = next(m.parameters()).device

        trf_t     = xp2torch(trf_out, requires_grad=is_train).to(device)
        pos_ids_t = pos_ids.to(device)
        morph_t   = morph_mat.to(device)

        # ── 4. Forward pass ────────────────────────────────────────────
        output_t  = m(trf_t, pos_ids_t, morph_t)

        # ── 5. Convert output back to Thinc/NumPy array ───────────────
        output_xp = torch2xp(output_t)

        def backprop(dOutput: Floats2d) -> List:
            # Convert incoming gradient to torch
            dOutput_t = xp2torch(dOutput).to(device)

            # PyTorch autograd computes all gradients
            output_t.backward(dOutput_t)

            # Pass transformer gradient back through TransformerListener
            if trf_t.grad is not None:
                trf_bp(torch2xp(trf_t.grad))

            # Zero PyTorch gradients for next batch
            m.zero_grad()

            return []   # no gradient w.r.t. docs input

        return output_xp, backprop

    def init(
        model: Model,
        X: Optional[List[Doc]] = None,
        Y=None,
    ) -> None:
        # Initialise transformer listener
        model.get_ref("tok2vec").initialize(X=X)

        # Resolve transformer output width
        trf_width = model.get_ref("tok2vec").get_dim("nO") or 768
        nO_actual = nO or hidden_width

        morph_vocab = model.attrs["morph_vocab"]

        # Build PyTorch module
        torch_module = ConcatPOSMorphModule(
            trf_width    = trf_width,
            pos_width    = pos_width,
            morph_width  = morph_width,
            morph_vocab  = morph_vocab,
            hidden_width = hidden_width,
            nO           = nO_actual,
        )

        # Move to GPU if spaCy is using GPU
        ops = model.ops
        if ops.__class__.__name__ in ("CupyOps", "NumpyOps"):
            if torch.cuda.is_available():
                torch_module = torch_module.cuda()

        model.attrs["torch_model"] = torch_module

    def to_disk(path, exclude=()):
        torch_model = model.attrs.get("torch_model")
        if torch_model is not None:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            torch.save(
                torch_model.state_dict(),
                p / "torch_model.pt"
            )

    def from_disk(path, exclude=()):
        p           = Path(path)
        state_dict  = torch.load(p / "torch_model.pt")
        torch_model = model.attrs.get("torch_model")
        if torch_model is not None:
            torch_model.load_state_dict(state_dict)
        return model

    model = Model(
        "concat_pos_morph_tagger",
        forward,
        init=init,
        refs  = {"tok2vec": tok2vec},
        attrs = {
            "torch_model": None,
            "morph_vocab": 2048,   # hash space for morph features
        },
        dims  = {"nO": nO},
    )

    # Attach serialisation methods
    model._func_to_disk  = to_disk
    model._func_from_disk = from_disk

    return model