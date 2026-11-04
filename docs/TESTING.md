# Modular architecture verification

Verified on Windows / Python 3.12 / Edge, 4 November 2026:

- 80 Python tests passed: core detector and file parsing, Django API, model setup, accuracy metrics and host integration.
- 3 frontend API-client tests passed; Vite production build passed.
- Real browser uploads: AI text, human text, PDF, DOCX, short text, image and damaged PDF. Checked percentages, image disclosures, protected assets, session isolation, paste flow and mobile saved-report access.
- Two reusable React instances mounted on a test host page. Parent body, heading and button styles remained unchanged; all control IDs were unique; module navigation left the host URL unchanged.
- Django app mounted at a different parent URL prefix. Namespaced reverse lookup worked; CSRF remained enforced; the module's streaming upload limit did not affect the parent's upload endpoint.
- Python wheel built successfully. It contains core, Django adapter and file-limit resources, but no standalone host, scripts, model weights or runtime data. Its core imports without Django and without modifying Python import paths.

The retired Tkinter and duplicate HTML-report tests were removed with those implementations. Core and web tests remain, with additional integration tests. These checks do not prove compatibility with an unseen parent application; its dependency lockfile, middleware, authentication, storage and queue still need to be connected as described in INTEGRATION.md.

This refactor does not train model weights or claim improved detection accuracy.
