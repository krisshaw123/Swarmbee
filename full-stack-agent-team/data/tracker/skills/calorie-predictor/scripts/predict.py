#!/usr/bin/env python3
"""
Calorie Predictor — Predict total meal calories from a food image.

Usage:
    python3 predict.py <image_path>
    python3 predict.py <image_path> --model /path/to/Mymodel

Dependencies: paddlepaddle, Pillow, numpy
"""

import argparse
import os
import sys
import numpy as np
from PIL import Image
import paddle
import paddle.nn as nn
import paddle.vision.models


# ---------------------------------------------------------------------------
# Model definition — must match the trained architecture exactly
# ---------------------------------------------------------------------------

class CalorieNetwork(paddle.nn.Layer):
    """ResNet152 backbone + MLP head for calorie regression."""

    def __init__(self):
        super(CalorieNetwork, self).__init__()
        self.resnet = paddle.vision.models.resnet152(pretrained=False, num_classes=0)
        self.flatten = paddle.nn.Flatten()
        self.linear_1 = paddle.nn.Linear(2048, 512)
        self.linear_2 = paddle.nn.Linear(512, 256)
        self.linear_3 = paddle.nn.Linear(256, 1)
        self.relu = paddle.nn.ReLU()
        self.dropout = paddle.nn.Dropout(0.2)

    def forward(self, inputs):
        y = self.resnet(inputs)
        y = self.flatten(y)
        y = self.linear_1(y)
        y = self.linear_2(y)
        y = self.relu(y)
        y = self.dropout(y)
        y = self.linear_3(y)
        return y


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def load_model(model_path):
    """Load the trained calorie model from disk."""
    model = CalorieNetwork()
    params = paddle.load(model_path)
    model.load_dict(params)
    model.eval()
    return model


def predict_calorie(model, image_path, image_size=256):
    """
    Predict calorie value for a single food image.

    Returns:
        float: predicted calories (kcal)
    """
    im = Image.open(image_path).convert('RGB')
    im = im.resize((image_size, image_size), Image.LANCZOS)
    im = np.array(im).astype('float32') / 255.0
    im = im.transpose(2, 0, 1)  # HWC → CHW
    tensor = paddle.to_tensor(im).reshape((1, 3, image_size, image_size))

    with paddle.no_grad():
        result = model(tensor)

    return result.tolist()[0][0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Predict meal calories from a food image.'
    )
    parser.add_argument(
        'image',
        help='Path to food image (jpg/png)',
    )
    parser.add_argument(
        '--model', '-m',
        default=None,
        help='Path to model weights file (default: $WORKSPACE/Mymodel)',
    )
    parser.add_argument(
        '--image-size', '-s',
        type=int, default=256,
        help='Resize dimension (default: 256)',
    )
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print(f"Error: image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    # Resolve model path
    model_path = args.model
    if model_path is None:
        # Default: look in the workspace-tracker directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workspace = os.environ.get(
            'WORKSPACE',
            os.path.join(os.path.expanduser('~'), '.openclaw', 'workspace-tracker'),
        )
        model_path = os.path.join(workspace, 'Mymodel')

    if not os.path.isfile(model_path):
        print(f"Error: model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading model from {model_path} ...", file=sys.stderr)
    model = load_model(model_path)

    print(f"Predicting calories for: {args.image}", file=sys.stderr)
    raw = predict_calorie(model, args.image, image_size=args.image_size)
    calories = raw - 400  # calibration offset

    # Output just the number for easy piping, details to stderr
    print(f"{calories:.0f} kcal")


if __name__ == '__main__':
    main()
