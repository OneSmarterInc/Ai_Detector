# Integrating AI File Inspector

The reusable boundaries are `ai_file_inspector.core`, the optional `ai_file_inspector.django_app`, and the React `AiFileInspector` export. The standalone host is an example, not a requirement. Do not copy its Django settings or its bootstrap script into your existing application.

## Existing Django application

1. Install the package into the host environment: `python -m pip install "path/to/AI-File-Inspector[web]"`. Review its dependency constraints against your existing lockfile; use that lockfile for deployment. The core-only install omits Django. A source installation does not include model weights.
2. Set the environment variable `AI_FILE_INSPECTOR_MODEL_DIR` to the verified Gradient artifact directory **before importing the package**, including in worker processes. Use `python scripts/setup_model.py --model-dir <directory>` from this checkout to download the pinned model. Runtime verifies its hashes; inference stays local.
3. Add `ai_file_inspector.django_app.apps.AiFileInspectorConfig` to `INSTALLED_APPS`. Keep your own session, CSRF and, when applicable, authentication middleware.
4. Configure private writable storage outside public static/media directories:

```python
AI_FILE_INSPECTOR = {
    "DATA_DIR": BASE_DIR / "private-data" / "ai-file-inspector",
    "MAX_QUEUED_JOBS": 5,
    # Optional: dotted callable accepting a string job UUID.
    # "SUBMIT_JOB": "your_app.tasks.enqueue_inspector_job",
}
```

5. Mount the namespaced URL set wherever it fits:

```python
path("tools/writing-check/", include("ai_file_inspector.django_app.urls")),
```

6. Run `python manage.py migrate`. The app label and database table use the `ai_file_inspector` namespace. URL names such as `ai_file_inspector:job-detail` support Django `reverse()`.

The app uses the host's database and cookies, not a separate database or authentication system. Authenticated users own reports by their user ID; otherwise reports belong to their browser session. The host must enforce its own login/access policy if anonymous scans are not allowed. Reports created anonymously are not automatically transferred to an account. Uploaded copies, assets and reports have the same owner checks. No static catch-all routes, middleware, server, migration command or filesystem initialization run when the reusable package is imported.

Upload limits are enforced on this module's endpoint. Do not add its upload handler globally. Host reverse-proxy limits and Django body/file-count limits can impose stricter limits; align them with your intended deployment. Ordinary CSRF protection remains enabled. Same-origin integration is the default; cross-origin hosting requires the host's own CORS, credentials and CSRF configuration.

## Existing React application

Install the local frontend package (`npm install /path/to/AI-File-Inspector/frontend`) or copy its `src` module into your repository. It exports source JSX and CSS Modules, so your existing bundler must support both. React and React DOM are peer dependencies; the module does not bundle another React runtime. Keep your existing React version if it satisfies the declared range.

```jsx
import {AiFileInspector} from 'ai-file-inspector-portal';

<AiFileInspector apiBaseUrl="/tools/writing-check/" />
```

`apiBaseUrl` controls requests, image URLs and report downloads. Optional `fetchImpl` accepts the same arguments and returns the same response interface as `fetch`, allowing a host adapter. Direct image/download requests use browser cookies, so an adapter alone does not add bearer authorization to those URLs. Use the documented cookie/session integration unless you implement a host-authorized asset/download flow.

The component neither creates a React root nor installs a router. It uses CSS Modules, local `--afi-*` variables and instance-specific control IDs. Base element rules are scoped to its root. It does not import the standalone body reset. `localMode` defaults to false; only the standalone demo sets it true to describe local processing accurately. Internal New scan navigation never redirects the parent application's page.

## Core-only use

```python
from pathlib import Path
from ai_file_inspector.core.detector import analyze
from ai_file_inspector.core.scanner import inspect_file

estimate = analyze("Your English prose here...")
assets = Path("private-scan-assets")
assets.mkdir(exist_ok=True)
result = inspect_file(Path("document.docx"), assets, [0])
```

The core has no Django or React dependency. It returns dictionaries and leaves storage/HTTP/UI decisions to the caller. Keep the asset counter unique across files in a shared output directory. Raw core results can contain local paths; the Django adapter replaces the top-level path before returning results to users.

## Jobs and scaling

The included executor is intentionally one worker per process for the local portal. It is not a durable distributed queue. A host queue should call `ai_file_inspector.django_app.worker.run_job(job_id)` in a configured Django worker process. Use `SUBMIT_JOB` to enqueue that function through your existing task system, and ensure workers share the same database, model artifacts and private storage. No queue dependency is installed by this module.

Queue admission is a local best-effort limit, not a distributed quota. Multiple workers/processes can load separate copies of the large model; set concurrency according to available memory. Model inference is serialized within each process. The standalone launcher marks interrupted jobs failed on startup; it does not automatically resume them. A host must define its own retry/recovery policy and must not call standalone recovery while active workers are running.

## Configuration and compatibility

- `AI_FILE_INSPECTOR_MODEL_DIR`: model artifact path, set before imports.
- `AI_FILE_INSPECTOR["DATA_DIR"]`: private scan storage; required by the Django adapter.
- `AI_FILE_INSPECTOR["SUBMIT_JOB"]`: optional host task-submission callable.
- `AI_FILE_INSPECTOR["MAX_QUEUED_JOBS"]`: local admission limit, default 5.
- Standalone only: `AI_FILE_INSPECTOR_DATA_DIR`, `--port`, `--no-browser`.
- Frontend development only: `AI_FILE_INSPECTOR_DEV_API` controls the Vite proxy target.

Model weights and thresholds are unchanged. All sections of extracted eligible text are now scored; the former document-character, section-count and PDF-page cutoffs are removed. The optional progress callback on analyze/inspect_file reports ongoing work. AI-like percentages describe classified sections, not measured authorship. See the accuracy and file-limit documentation before relying on results.
