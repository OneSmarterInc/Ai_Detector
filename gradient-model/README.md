---
library_name: transformers.js
base_model: ShantanuT01/gradient-ai-text-detector
base_model_relation: quantized
pipeline_tag: text-classification
language:
- en
license: mit
tags:
- onnx
- text-classification
- ai-generated-text-detection
- deberta-v2
- quantization
---

# Gradient AI Text Detector, ONNX (fp32 + fp16 + q4)

ONNX exports of [`ShantanuT01/gradient-ai-text-detector`](https://huggingface.co/ShantanuT01/gradient-ai-text-detector),
a DeBERTa-v3-large binary classifier producing P(AI). Built for
[transformers.js](https://huggingface.co/docs/transformers.js) so the model can run in
a browser with no server.

| file | size | `dtype` | accuracy vs fp32 |
| --- | --- | --- | --- |
| `onnx/model.onnx` | 1661 MB | `fp32` | reference (logits match PyTorch to 1.5e-05) |
| `onnx/model_fp16.onnx` | 832 MB | `fp16` | max ΔP 0.0004 over 12 passages |
| `onnx/model_q4.onnx` | 408 MB | `q4` | max ΔP 0.06 over 12 passages |

**`q4` is the default**: weight-only 4-bit, so it is both half of `fp16` and within
0.06 of the reference, with no verdict flips at a 0.5 threshold across the 12
fixture passages. Use `fp16` when closer-to-exact scores matter more than download
size.

An int8 build (`onnx/model_quantized.onnx`, 612 MB) previously shipped here and was
removed. Dynamic int8 drifted 0.30 mid-range: larger *and* roughly five times less
accurate than `q4`. Its error comes from quantizing activations, which is also why
calibrated static int8 measured worse still (0.63-0.99).

## Usage

```js
import { AutoModelForSequenceClassification, AutoTokenizer } from '@huggingface/transformers';

const repo = 'batmac/gradient-ai-text-detector-onnx';
const tokenizer = await AutoTokenizer.from_pretrained(repo);
const model = await AutoModelForSequenceClassification.from_pretrained(repo, { dtype: 'q4' });

const text = "In today's rapidly evolving digital landscape, organizations must leverage synergistic strategies.";
const inputs = await tokenizer(text, { padding: true, truncation: true, max_length: 512 });
const { logits } = await model(inputs);
const pAi = 1 / (1 + Math.exp(-logits.tolist()[0][0])); // sigmoid
```

`num_labels` is 1: the model emits a single logit and **the caller applies `sigmoid`**.
Do not use the `text-classification` pipeline, which applies `softmax` to that single
logit and returns `score: 1` for every input.

## Export and quantization

Exports were produced with `optimum` at opset 17, dynamic batch and sequence dims,
inputs `input_ids` and `attention_mask` only. `fp16` is a straight
`convert_float_to_float16` with `keep_io_types`.

`q4` composes three steps, all weight-only, so activations stay at higher precision:

1. `MatMulNBits` int4 (RTN, group size 32) for the matmuls;
2. `quantize_dynamic` restricted to `Gather` for the embedding table in int8;
3. `convert_float_to_float16` for the remainder, with the int8/QDQ ops and
   `MatMulNBits` blocked.

Results are validated against the fp32 logits of the original PyTorch model: the
`fp32` export matches to 1.5e-05, and the quantized variants are checked for score
drift and for verdict flips on passages that sit near the 0.5 decision boundary.

`P(AI)` is not a calibrated authorship probability, and the upstream card warns
against sole reliance on it for high-stakes decisions. MIT, inherited from the
original model.
