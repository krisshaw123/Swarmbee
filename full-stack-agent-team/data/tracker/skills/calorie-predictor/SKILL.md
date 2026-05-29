---
name: calorie-predictor
description: "Predict total calorie (kcal) of a meal from a food photo using a PaddlePaddle ResNet152 regression model."
---

# Calorie Predictor

Uses a pretrained PaddlePaddle model (ResNet152 backbone → MLP → scalar calorie output) to predict total meal calories from a single food image.

## Model Info

- **Architecture:** ResNet152 → Flatten → Linear(2048,512) → Linear(512,256) → ReLU → Dropout(0.2) → Linear(256,1)
- **Training data:** ~400 labeled food images from Chinese cafeteria meals and web photos
- **Output:** Single calorie estimate (kcal) for the whole image
- **Input:** RGB image, auto-resized to 256×256

## Usage

```bash
python3 scripts/predict.py <image_path> [--model MODEL_PATH]
```

Default model path: `$WORKSPACE/Mymodel`

## Script

See `scripts/predict.py` for the self-contained inference script.

## Caveats

- Model was trained on limited data (~50–400 samples); results are approximate.
- Best on Chinese-style cafeteria/plated meals.
- Does not decompose by food type — single total only.
- Single-image inference, no batch support in script.
- Run on CPU (no CUDA required).
