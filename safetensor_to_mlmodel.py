import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
import coremltools as ct
from safetensors.torch import load_file


# ---------------------------------------------------------------------------
# Model definition — derived from tensor names in MHD.safetensors
# ---------------------------------------------------------------------------

class ConvBlock(nn.Module):
