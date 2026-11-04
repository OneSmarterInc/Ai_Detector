# AI File Inspector

A self-contained English writing and file inspection module, with a React interface and an optional Django API. Gradient (DeBERTa-v3-large, Q4 ONNX) runs locally on the server CPU. Writing estimates are not proof of AI authorship.

## Project structure

```text
backend/
  ai_file_inspector/
    core/                 Detector, file parsing, percentage calculation
    django_app/           Namespaced API, models, migrations, job adapter
    resources/            Canonical file-limit guide
  standalone/             Local Django host; not part of the installed package
frontend/
  src/
    components/           Report and icon components
    services/             Configurable HTTP client
    styles/               Scoped CSS Modules
    AiFileInspector.jsx   Reusable feature component
    index.js              Public frontend export
    main.jsx              Standalone React entry only
  tests/                  API tests and host-integration fixture
scripts/                  Local launcher, model setup and evaluation tools
tests/                    Core, setup, evaluation and integration tests
models/gradient/          Model provenance; downloaded weights ignored by Git
docs/                     Integration, design and accuracy documentation
runtime/                  Local dependencies, data, reports and backups (ignored)
```

The reusable code never alters Python import paths, starts a server, creates a database, runs migrations or adds global browser styles. Only the standalone launcher performs local setup. Old Tkinter and duplicate HTML-report implementations have been retired; their files and existing reports are preserved in the local upgrade backup.

## Run locally on Windows

Install Python 3.12 x64 and Node.js 22.12 or newer, then run **Setup Windows.bat** once. It installs this package with its Django extra, downloads verified model files and builds React. Open **Start Portal.bat**. The browser opens http://127.0.0.1:8000; keep the server window open. The installed D: copy includes its existing dependencies and model.

Original documents are unchanged. Saved copies and reports live in `runtime/web-data`. Use the same browser session to reopen anonymous reports. Delete a scan in the portal to remove its saved copies. This standalone launcher uses Django's development server and one background worker; it is intended for one local computer.

## Integrate into an existing application

See [docs/INTEGRATION.md](docs/INTEGRATION.md) for Python installation, namespaced Django URLs/settings, React imports, configurable API paths, ownership rules, and the existing-queue adapter. The core can also be called without Django. Integrate the reusable package and component, not the standalone host configuration.

## Model and percentages

Original: https://huggingface.co/ShantanuT01/gradient-ai-text-detector

Pinned ONNX conversion: https://huggingface.co/batmac/gradient-ai-text-detector-onnx/tree/776d0164ba0de631036c70f6a146d68a7cd4ea4e

The report displays three equal percentages: **Human**, **AI** and **Uncertain**, under "Estimated content breakdown". These are display labels for the length-weighted shares of sections classified as human-like, AI-like or uncertain; the detector and calculation are unchanged. A 60% AI-like share does not prove that AI wrote 60% of the words. Short/non-English content may have no estimate; all sections of extracted eligible text are checked. Image patterns do not identify AI-generated images. The detailed guide is in `backend/ai_file_inspector/resources/file-limits.txt` and inside the portal.

Weights are unchanged. Fine-tuning requires correctly labelled training data and independent testing. See [accuracy follow-up](docs/ACCURACY-FOLLOWUP.txt) and [model comparison](docs/MODEL-COMPARISON.txt) for previous results and limitations.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python manage.py test ai_file_inspector.django_app tests
cd frontend
npm ci
npm test
npm run build
```

For frontend development, run Django on port 8000 and `npm run dev` inside frontend. `frontend/tests/host.html` mounts two module instances alongside host controls for browser isolation checks. `python scripts/evaluate_accuracy.py --help` describes labelled-data evaluation. Dependency manifests have one Python source of truth (`pyproject.toml`) and one frontend lockfile; heavy model artifacts and runtime data are excluded from Git.
