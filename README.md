# AI File Inspector — React + Django

A local browser portal for checking English writing, hidden characters, file metadata and image patterns. The interface is React; Django handles uploads, background checks, session access and reports. SQLite stores scan history. Gradient (DeBERTa-v3-large, Q4 ONNX) runs locally on the CPU.

## Start on Windows

1. Install 64-bit Python 3.12 and Node.js 22.12 or newer.
2. Download this repository into a writable folder.
3. Run **Setup Windows.bat**. This installs Python libraries, downloads the pinned model, and builds React with `npm ci` and `npm run build`.
4. Run **Start Portal.bat** (Start Inspector.bat opens the same portal).
5. Open http://127.0.0.1:8000 if the browser does not open automatically. Keep the server window open.

Scans do not send documents to an external service. Uploads are copies stored under `web-data/jobs`; originals are unchanged. Reports belong to the browser session that created them. Clearing cookies loses access to that history. Delete a scan from the portal to remove its saved copies and report. Old desktop reports remain in `reports/` and are not imported.

This launcher serves one local computer using Django's development server, one background scanning worker and SQLite. It is not a public production deployment. A shared hosted service needs authentication, a production server, a durable job queue and deployment-specific limits.

## Reading the percentage

The percentage means **the share of checked text in sections flagged AI-like**. Sections are weighted by token length. Scores at least 80/100 are AI-like, scores at most 20/100 are human-like, and the middle is uncertain. Rounded shares add to 100%.

Example: equal-length sections with two AI-like, one human-like and one uncertain produce **50% AI-like, 25% human-like, 25% uncertain**. This does not establish that half the words were actually written by AI. A short one-section document can show 100% AI-like without 100% certainty. Unchecked content has no percentage. Sampling and extraction limits are displayed separately.

## Model and accuracy

- Original model: https://huggingface.co/ShantanuT01/gradient-ai-text-detector
- Q4 conversion: https://huggingface.co/batmac/gradient-ai-text-detector-onnx
- Conversion revision: `776d0164ba0de631036c70f6a146d68a7cd4ea4e`.
- Runtime verifies model, tokenizer and configuration SHA-256 hashes. No remote model code is executed.
- The model emits a single AI logit, converted using sigmoid. Scores are uncalibrated writing-pattern signals, not probabilities of authorship.

**This interface update does not retrain model weights or demonstrate improved detection accuracy.** The earlier 138-example comparison gave Gradient 128 correct, 2 wrong, 8 uncertain. A harder 96-example check gave 69 correct, 15 wrong, 12 uncertain, including human false alarms. These small datasets are not an overall accuracy guarantee. See MODEL-COMPARISON.txt and ACCURACY-FOLLOWUP.txt.

Weights can be improved through fine-tuning. We need correctly labelled, permitted human, AI and edited examples across the writing types users actually upload. Split by source/prompt into training, development and untouched testing data. Tune the original trainable checkpoint, not the deployed Q4 ONNX file. Measure human false alarms, AI misses, uncertainty and results by writing type. Export and quantize a candidate, then retest that exact artifact against the existing model on the same unseen examples before replacing it. No such training has been performed in this update.

## File limits

See **FILE-LIMITS.txt**, also available inside the portal. Web batches accept up to 10 files, 100 MiB per file and 500 MiB total. Pasted text is capped at 200,000 characters. Writing estimates require at least 100 English prose words. PDF scanning considers the first 300 pages; DOCX has no fixed page-count cap. AI scoring considers at most 200,000 characters and 12 sections of up to 480 tokens. Images get pattern/file checks, not AI-image classification. No OCR is included.

## Development and tests

`python manage.py test portal` runs the web/API tests. `python -m unittest test_detector test_inspector` runs detector and file-processing tests. Model fixtures require the downloaded model and dependencies. Run `npm run build` inside frontend for the production interface. For frontend development use `npm run dev` with Django on port 8000.

Main files: `frontend/src/App.jsx`, `portal/views.py`, `portal/worker.py`, `portal/analysis.py`, `ai_detector.py`, `inspector.py`. The old Tkinter UI and HTML report code are retained for compatibility only; the default launcher now uses React and Django. Model weights, dependencies, uploaded documents, secrets and generated reports are excluded from Git.
