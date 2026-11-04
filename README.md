# AI File Inspector

A local Windows desktop tool that checks English writing with **Gradient AI Text Detector (DeBERTa-v3-large, Q4)** and creates a report in simple English. It also inspects hidden characters, file metadata and image patterns.

## Start on Windows

1. Install **64-bit Python 3.12** with Tcl/Tk support.
2. Clone or download and extract this repository into a writable folder.
3. Run **Setup Windows.bat** once. Internet access is needed to install libraries and download the pinned model (about 417 MB including its tokenizer).
4. Run **Start Inspector.bat** and select your files.

Scans run locally without an API key or document upload. The first scan may take longer while the model loads. Reports are saved in `reports/` and open in your browser.

The separately shared Windows ZIP already includes the model and libraries. Follow its `START-HERE.txt` instead of these source-installation steps. Neither distribution includes Python itself.

## What it checks

- AI writing estimates for text, readable PDF and Word `.docx` files.
- At least **100 words of English prose** are required. Code and other languages are not supported by this detector.
- Clear labels: **Looks AI-written**, **Looks human-written**, **Not sure**, or **Not checked**.
- Hidden Unicode characters and metadata are reported separately from the writing estimate.
- Images, technical details and raw scores stay hidden until opened.
- Original files are not modified. Scanned image-only PDFs need OCR, which is not included.

The result is an estimate, not proof of authorship. A score is neither a percentage of AI-written words nor a calibrated probability. Creative writing, unfamiliar writing and heavily edited text can cause mistakes. Image checks do not classify images as AI-generated or detect SynthID.

## Model and evaluation

Source: [ShantanuT01/gradient-ai-text-detector](https://huggingface.co/ShantanuT01/gradient-ai-text-detector).
Q4 conversion: [batmac/gradient-ai-text-detector-onnx](https://huggingface.co/batmac/gradient-ai-text-detector-onnx).

The exact conversion is pinned to `776d0164ba0de631036c70f6a146d68a7cd4ea4e`. Downloads and runtime files are verified with SHA-256. Source cards, configuration and provenance are in `gradient-model/`. The model emits one AI logit; the app applies sigmoid, then combines passage scores using the documented uncertainty rules.

Across 138 limited comparison examples, the old model gave 112 correct, 17 wrong and 9 uncertain results; Gradient gave 128 correct, 2 wrong and 8 uncertain results. These are **sample-specific results, not an overall accuracy guarantee**. Dataset/training overlap is possible. Fresh AI examples came from one assistant. See [comparison details](docs/MODEL-COMPARISON.txt) for selection, separate confirmation results and limitations.

The app passed 70 automated tests, an installed desktop scan and browser-report checks. The historical comparison document mentions backup paths from the original installation; those backups are not part of this repository.

## Developer setup

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe setup_model.py
.venv\Scripts\python.exe -B run_inspector.py --check
.venv\Scripts\python.exe -B -m unittest discover -p "test_*.py"
```

Tests use real local model inference and Tk, so run them on a Windows desktop session after downloading the model.

Command-line scanning:

```powershell
.venv\Scripts\python.exe -B run_inspector.py sample.txt --output reports\sample
```

The output folder must not already exist. To check known-origin examples, see `accuracy-checker/`. Its JSONL labels must be known `human` or `ai` origins; do not use guessed labels from another detector.

## Project files

| File | Purpose |
|---|---|
| `inspector.py` | File extraction and inspection |
| `ai_detector.py` | Local Gradient inference and score rules |
| `desktop_ui.py` | Native file picker and background scanning |
| `report_view.py` | Offline HTML report |
| `setup_model.py` | Pinned, hash-verified model download |
| `run_inspector.py` | Portable project launcher |
| `test_*.py` | Application tests |
| `examples/` | Known-origin demonstration texts |
| `accuracy-checker/` | Evaluation tool and recorded results |

Large model weights, installed libraries, local environments, scan reports and backups are excluded from Git. The model provider declares MIT licensing; its original source cards are retained. Third-party model and library terms continue to apply. No additional license for the project's own source is asserted here.

## Harder accuracy follow-up (4 November 2026)

A separate 96-text Beemo study covered human, original AI and expert-edited AI writing from ten generators. Gradient gave 69 correct origin decisions, 15 wrong and 12 uncertain. Cutoff changes and tested model combinations did not meet the improvement criteria, so the model and scoring rules remain unchanged. Curly-apostrophe word counting and mixed-passage explanations were repaired. See [the follow-up report](docs/ACCURACY-FOLLOWUP.txt). These results are sample-specific; expert-edited AI is evaluated as AI-origin, not entirely AI-written.

## File types and limits

Open **File limits** in the app for the full [file limits guide](FILE-LIMITS.txt).

| Type | Minimum for AI writing estimate | File and inspection limits |
|---|---|---|
| PDF | 100 English words; no minimum page-count rule | 100 MiB/file; inspect first 300 pages; up to 50 embedded images |
| DOCX | 100 English words; no page-count rule | 100 MiB/file, 200 MiB expanded; up to 50 embedded images |
| TXT, MD, HTML | 100 English words; no fixed character minimum | 100 MiB/file |
| CSV, JSON, PY, XML, TEX, LOG | AI writing estimate disabled | 100 MiB/file; file/text checks only |
| PNG, JPG/JPEG, WEBP, TIF/TIFF, BMP | No AI writing/image-authorship estimate | 100 MiB/file and 40 megapixels; first frame/page only |

For eligible prose, only the **first 200,000 extracted characters** are considered, before cleanup, and **up to 12 sections of 480 body tokens** are scored. Longer text is sampled and the report discloses partial coverage. A 300-page PDF is not necessarily fully scored by the AI model. PDFs above 300 pages are accepted if otherwise valid and within the file-size cap, but pages after 300 are skipped.

Images have no additional minimum dimensions for metadata checks. Pattern visualizations require at least 64 pixels on both sides after resizing to a maximum 1,600-pixel longest side. No OCR is included. There is no coded batch-count or combined-size cap; files are processed sequentially. The app labels its 100 MiB cap as "100 MB" (104,857,600 bytes).
