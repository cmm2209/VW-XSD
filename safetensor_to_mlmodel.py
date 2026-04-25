import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
import coremltools as ct
from safetensors.torch import load_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_safetensors(path: str) -> dict[str, torch.Tensor]:
    """Load all tensors from a .safetensors file."""
    print(f"[1/4] Loading tensors from: {path}")
    tensors = load_file(path)
    print(f"      Loaded {len(tensors)} tensor(s):")
    for name, t in tensors.items():
        print(f"        • {name:40s}  shape={str(t.shape):30s}  dtype={t.dtype}")
    return tensors


def infer_model_from_tensors(tensors: dict[str, torch.Tensor]) -> nn.Module:
    """
    Try to reconstruct a simple Sequential / Linear model from the weight
    keys found in the safetensors file.

    Supported naming conventions
    ----------------------------
    • Hugging Face-style  : model.layers.0.weight / model.layers.0.bias
    • Simple numbered     : 0.weight / 0.bias  or  layer0.weight / layer0.bias
    • Single-layer        : weight / bias

    For anything more complex you should subclass nn.Module yourself and
    load the state-dict with model.load_state_dict(tensors).
    """
    print("[2/4] Inferring model architecture …")

    import re

    layer_map: dict[int, dict[str, str]] = {}

    for key in tensors:
        # match patterns like "0", "layer_0", "layers.0", "model.layers.0"
        m = re.search(r"(\d+)\.(weight|bias)$", key)
        if m:
            idx  = int(m.group(1))
            kind = m.group(2)
            layer_map.setdefault(idx, {})[kind] = key
            continue

        # bare "weight" / "bias" → treat as single layer (index 0)
        if key in ("weight", "bias"):
            layer_map.setdefault(0, {})[key] = key

    if not layer_map:
        raise ValueError(
            "Could not automatically infer a layer structure from the tensor "
            "names. Please edit infer_model_from_tensors() to match your "
            "specific architecture."
        )

    # Build nn.Sequential from the collected layers
    layers: list[nn.Module] = []
    for idx in sorted(layer_map.keys()):
        entry = layer_map[idx]
        if "weight" not in entry:
            continue

        w = tensors[entry["weight"]]
        has_bias = "bias" in entry

        if w.ndim == 2:                          # Linear layer
            out_features, in_features = w.shape
            linear = nn.Linear(in_features, out_features, bias=has_bias)
            linear.weight = nn.Parameter(w.float())
            if has_bias:
                linear.bias = nn.Parameter(tensors[entry["bias"]].float())
            layers.append(linear)

        elif w.ndim == 4:                        # Conv2d layer
            out_ch, in_ch, kH, kW = w.shape
            conv = nn.Conv2d(in_ch, out_ch, kernel_size=(kH, kW), bias=has_bias)
            conv.weight = nn.Parameter(w.float())
            if has_bias:
                conv.bias = nn.Parameter(tensors[entry["bias"]].float())
            layers.append(conv)

        else:
            print(f"      ⚠  Skipping tensor '{entry['weight']}' "
                  f"(unsupported ndim={w.ndim})")

    if not layers:
        raise ValueError("No usable layers found – cannot build a model.")

    model = nn.Sequential(*layers)
    model.eval()
    print(f"      Built nn.Sequential with {len(layers)} layer(s).")
    return model


def build_example_input(model: nn.Module) -> torch.Tensor:
    """
    Create a random example input matching the first layer's expected shape.
    Uses torch.rand (not torch.zeros) to avoid issues with batch norm etc.
    """
    first_layer = next(
        (m for m in model.modules() if isinstance(m, (nn.Linear, nn.Conv2d))),
        None,
    )
    if first_layer is None:
        raise RuntimeError("No Linear or Conv2d layer found in model.")

    if isinstance(first_layer, nn.Linear):
        return torch.rand(1, first_layer.in_features)

    if isinstance(first_layer, nn.Conv2d):
        # Default spatial size 224×224 — override via --input-size if needed
        return torch.rand(1, first_layer.in_channels, 224, 224)

    raise RuntimeError("Unexpected layer type.")


def convert_to_mlmodel(
    model: nn.Module,
    example_input: torch.Tensor,
    output_path: str,
) -> None:
    """
    Trace the PyTorch model and convert it to a Core ML neural network
    (.mlmodel), following the official coremltools v6.3 conversion guide:

      - No convert_to parameter → produces a NeuralNetwork → saves as .mlmodel
      - Only TensorType inputs (no automatic ImageType)
      - Traced model is verified before conversion
    """
    print("[3/4] Tracing model …")

    # Model must be in eval mode before tracing
    model.eval()

    with torch.no_grad():
        traced_model = torch.jit.trace(model, example_input)

    # Verify the traced model runs correctly before converting
    print("      Verifying traced model …")
    with torch.no_grad():
        out = traced_model(example_input)
    print(f"      Traced model output shape: {out.shape}")

    print("      Converting to Core ML neural network (.mlmodel) …")

    # Omitting convert_to produces a NeuralNetwork, which saves as .mlmodel
    # Using only TensorType as recommended for non-image inputs
    mlmodel = ct.convert(
        traced_model,
        inputs=[ct.TensorType(shape=example_input.shape)],
    )

    # Attach metadata
    mlmodel.short_description = "Converted from .safetensors via safetensors2mlmodel"
    mlmodel.author            = "safetensors2mlmodel script"

    print(f"[4/4] Saving Core ML model to: {output_path}")
    mlmodel.save(output_path)
    print("      ✓ Done!")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a .safetensors file to Apple CoreML (.mlmodel)"
    )
    parser.add_argument(
        "input",
        help="Path to the input .safetensors file",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output path (default: same name as input with .mlmodel extension)",
    )
    parser.add_argument(
        "--input-size",
        nargs="+",
        type=int,
        default=None,
        metavar="DIM",
        help=(
            "Override the example-input shape, e.g. --input-size 1 3 224 224 "
            "for a 4-D conv input or --input-size 1 512 for a linear input"
        ),
    )
    parser.add_argument(
        "--state-dict-only",
        action="store_true",
        help="Print tensor names/shapes and exit without converting",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Error: file not found – {input_path}")
    if input_path.suffix.lower() != ".safetensors":
        print(f"Warning: expected a .safetensors extension, got '{input_path.suffix}'")

    tensors = load_safetensors(str(input_path))

    if args.state_dict_only:
        print("\nInspection-only mode – no conversion performed.")
        return

    model = infer_model_from_tensors(tensors)

    if args.input_size:
        example_input = torch.rand(*args.input_size)
        print(f"      Using user-supplied input shape: {list(example_input.shape)}")
    else:
        example_input = build_example_input(model)
        print(f"      Using inferred input shape:      {list(example_input.shape)}")

    output_path = args.output or str(input_path.with_suffix(".mlmodel"))

    convert_to_mlmodel(model, example_input, output_path)


if __name__ == "__main__":
    main()