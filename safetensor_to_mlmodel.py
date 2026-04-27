import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
import coremltools as ct
from safetensors.torch import load_file


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size):
        super().__init__()
        self.co = nn.Conv2d(
            in_channels, out_channels, kernel_size=kernel_size, padding="same"
        )

    def forward(self, x):
        return torch.relu(self.co(x))


class BiLSTMBlock(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.layer = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            bidirectional=True,
            batch_first=True,
        )

    def forward(self, x):
        out, _ = self.layer(x)
        return out


class OutputBlock(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.lin = nn.Linear(in_features, out_features)

    def forward(self, x):
        return self.lin(x)


class MHDModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.nn = nn.ModuleDict({
            "C_0":  ConvBlock(1,  32, (3, 13)),
            "C_3":  ConvBlock(32, 32, (3, 13)),
            "C_6":  ConvBlock(32, 64, (3, 9)),
            "C_9":  ConvBlock(64, 64, (3, 9)),
            "L_12": BiLSTMBlock(960, 200),
            "L_14": BiLSTMBlock(400, 200),
            "L_16": BiLSTMBlock(400, 200),
            "O_18": OutputBlock(400, 108),
        })

    def forward(self, x):
        x = self.nn["C_0"](x)
        x = self.nn["C_3"](x)
        x = self.nn["C_6"](x)
        x = self.nn["C_9"](x)

        batch, channels, height, width = x.shape
        x = x.permute(0, 3, 1, 2)
        x = x.reshape(batch, width, channels * height)

        x = self.nn["L_12"](x)
        x = self.nn["L_14"](x)
        x = self.nn["L_16"](x)
        x = self.nn["O_18"](x)
        return x


def load_and_build_model(safetensors_path: str) -> nn.Module:
    print(f"[1/4] Loading tensors from: {safetensors_path}")
    tensors = load_file(safetensors_path)
    print(f"      Loaded {len(tensors)} tensor(s).")

    print("[2/4] Building model and loading weights ...")
    model = MHDModel()

    prefix = "12376ee3-4f42-48e9-8fd5-47a6ae9d853d."
    stripped = {
        k.replace(prefix, ""): v
        for k, v in tensors.items()
    }

    missing, unexpected = model.load_state_dict(stripped, strict=False)

    if missing:
        print(f"      Warning - Missing keys: {missing}")
    if unexpected:
        print(f"      Warning - Unexpected keys: {unexpected}")
    if not missing and not unexpected:
        print("      All weights loaded successfully.")

    model.eval()
    return model


def convert_to_mlmodel(
    model: nn.Module,
    example_input: torch.Tensor,
    output_path: str,
) -> None:
    print("[3/4] Tracing and converting to Core ML ...")

    model.eval()
    with torch.no_grad():
        traced_model = torch.jit.trace(model, example_input)

    print("      Verifying traced model ...")
    with torch.no_grad():
        out = traced_model(example_input)
    print(f"      Output shape: {out.shape}")

    print("      Converting ...")
    mlmodel = ct.convert(
        traced_model,
        inputs=[ct.TensorType(shape=example_input.shape)],
    )

    mlmodel.short_description = "MHD Kraken OCR model converted from .safetensors"
    mlmodel.author = "safetensors2mlmodel script"

    print(f"[4/4] Saving to: {output_path}")
    mlmodel.save(output_path)
    print("      Done!")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert MHD.safetensors to Apple CoreML (.mlmodel)"
    )
    parser.add_argument("input", help="Path to the .safetensors file")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output path (default: input name with .mlmodel extension)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=15,
        help="Input image height in pixels (default: 15)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=256,
        help="Input image width / sequence length (default: 256)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Error: file not found - {input_path}")

    model = load_and_build_model(str(input_path))

    expected_lstm_input = 960
    if args.height * 64 != expected_lstm_input:
        sys.exit(
            f"Error: height ({args.height}) * 64 = {args.height * 64}, "
            f"but L_12 expects {expected_lstm_input}. "
            f"Try --height 15."
        )

    example_input = torch.rand(1, 1, args.height, args.width)
    print(f"      Example input shape: {list(example_input.shape)}")

    output_path = args.output or str(input_path.with_suffix(".mlmodel"))
    convert_to_mlmodel(model, example_input, output_path)


if __name__ == "__main__":
    main()
