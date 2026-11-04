import {
  useEffect,
  useRef,
  useState,
  useMemo,
  useId,
  useCallback,
} from "react";
import Icon from "./components/Icon.jsx";
import FileResult from "./components/FileResult.jsx";
import { createInspectorApi } from "./services/inspectorApi.js";
import { classNames } from "./styles/classNames.js";
const formatSize = (n) =>
  n >= 1048576
    ? `${(n / 1048576).toFixed(1)} MB`
    : `${Math.max(1, Math.ceil(n / 1024))} KB`;
const active = (job) => job && ["queued", "running"].includes(job.status);
export default function AiFileInspector({
  apiBaseUrl = "/api/ai-file-inspector/",
  fetchImpl = globalThis.fetch,
  localMode = false,
}) {
  const api = useMemo(
    () => createInspectorApi(apiBaseUrl, fetchImpl),
    [apiBaseUrl, fetchImpl],
  );
  const instanceId = useId();
  const contentId = instanceId + "-content";
  const [info, setInfo] = useState(null),
    [error, setError] = useState(""),
    [files, setFiles] = useState([]),
    [text, setText] = useState(""),
    [mode, setMode] = useState("files");
  const [job, setJob] = useState(null),
    [history, setHistory] = useState([]),
    [page, setPage] = useState("scan"),
    [sending, setSending] = useState(false),
    [dragging, setDragging] = useState(false),
    [notice, setNotice] = useState("");
  const filePicker = useRef(null),
    folderPicker = useRef(null);
  const busy = sending || active(job);
  const jobId = job?.id;
  const jobStatus = job?.status;
  const refresh = useCallback(
    () => api.request("jobs/").then((data) => setHistory(data.jobs)),
    [api],
  );
  useEffect(() => {
    let live = true;
    api
      .request("info/")
      .then((data) => {
        if (live) setInfo(data);
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    api
      .request("jobs/")
      .then((data) => {
        if (live) setHistory(data.jobs);
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [api]);
  useEffect(() => {
    if (!jobId || !["queued", "running"].includes(jobStatus)) return;
    let cancelled = false,
      timer;
    const poll = async () => {
      try {
        const next = await api.request(`jobs/${jobId}/`);
        if (cancelled) return;
        setJob(next);
        if (!active(next)) await refresh();
      } catch (e) {
        if (!cancelled) {
          setError(
            "Could not refresh the scan. Check that the server is still running.",
          );
        }
      } finally {
        if (!cancelled) timer = setTimeout(poll, 1500);
      }
    };
    timer = setTimeout(poll, 1000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [api, jobId, jobStatus, refresh]);
  function addFiles(incoming, folder = false) {
    if (busy || !info) return;
    setError("");
    setNotice("");
    const all = Array.from(incoming);
    const supported = all.filter((f) =>
      info.extensions.includes("." + f.name.split(".").pop().toLowerCase()),
    );
    if (supported.length !== all.length) {
      if (!folder) {
        setError(
          "Unsupported file type. Open File limits to see the supported formats.",
        );
        return;
      }
      setNotice(
        `${all.length - supported.length} unsupported file(s) skipped.`,
      );
    }
    const merged = [...files];
    for (const f of supported)
      if (
        !merged.some(
          (x) =>
            x.name === f.name &&
            x.size === f.size &&
            x.lastModified === f.lastModified,
        )
      )
        merged.push(f);
    if (merged.length > info.max_files) {
      setError(
        "Choose up to 10 files per batch. For a folder, select a smaller group of files.",
      );
      return;
    }
    if (
      merged.some((f) => f.size > info.max_file_bytes) ||
      merged.reduce((n, f) => n + f.size, 0) > info.max_batch_bytes
    ) {
      setError("Use files up to 100 MB each and 500 MB per batch.");
      return;
    }
    setFiles(merged);
  }
  async function scan(event) {
    event.preventDefault();
    if (!info || busy) return;
    setError("");
    setSending(true);
    const body = new FormData();
    if (mode === "files") files.forEach((f) => body.append("files", f));
    else body.append("text", text);
    try {
      const next = await api.request("jobs/", {
        method: "POST",
        headers: {
          "X-CSRFToken": info.csrf_token,
        },
        body,
      });
      setJob(next);
      setPage("scan");
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  }
  async function openJob(id) {
    setError("");
    try {
      setJob(await api.request(`jobs/${id}/`));
      setPage("scan");
    } catch (e) {
      setError(e.message);
    }
  }
  async function removeReport() {
    if (!job || active(job)) return;
    setError("");
    try {
      await api.request(`jobs/${job.id}/`, {
        method: "DELETE",
        headers: {
          "X-CSRFToken": info.csrf_token,
        },
      });
      setJob(null);
      await refresh();
      setNotice(
        "Report and uploaded copies deleted. Your original files were not changed.",
      );
    } catch (e) {
      setError(e.message);
    }
  }
  function newScan() {
    setPage("scan");
    if (!active(job)) {
      setJob(null);
      setFiles([]);
      setText("");
      setNotice("");
      setError("");
    }
  }
  return (
    <div className={classNames("root app-shell")}>
      <a className={classNames("skip-link")} href={`#${contentId}`}>
        Skip to content
      </a>
      <aside className={classNames("sidebar")}>
        <button
          type="button"
          className={classNames("brand")}
          onClick={newScan}
          aria-label="AI File Inspector home"
        >
          <span className={classNames("brand-mark")}>
            <Icon name="file" />
          </span>
          <span>
            AI File
            <br />
            <strong>Inspector</strong>
          </span>
        </button>
        <nav aria-label="Main navigation">
          <button
            className={classNames(
              page === "scan" ? "nav-button selected" : "nav-button",
            )}
            onClick={newScan}
          >
            <Icon name="plus" />
            New scan
          </button>
          <button
            className={classNames(
              page === "limits" ? "nav-button selected" : "nav-button",
            )}
            onClick={() => setPage("limits")}
          >
            <Icon name="info" />
            File limits
          </button>
        </nav>
        <section className={classNames("history")}>
          <h2>Recent scans</h2>
          {history.length === 0 ? (
            <p className={classNames("small")}>
              Your reports will appear here.
            </p>
          ) : (
            <ul>
              {history.map((h) => (
                <li key={h.id}>
                  <button
                    className={classNames(
                      job?.id === h.id
                        ? "history-button current"
                        : "history-button",
                    )}
                    onClick={() => openJob(h.id)}
                  >
                    <span>
                      {h.files[0]?.name || "New scan"}
                      {h.files.length > 1 ? ` +${h.files.length - 1}` : ""}
                    </span>
                    <small>
                      {h.status === "complete"
                        ? "Ready"
                        : h.status === "failed"
                          ? "Stopped"
                          : h.status === "queued"
                            ? "Waiting"
                            : "Checking"}
                    </small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        <div className={classNames("local-note")}>
          <span className={classNames("local-dot")} />
          {localMode ? "Runs on this computer" : "AI File Inspector"}
          <p>
            {localMode
              ? "Files stay in your local portal. No external AI API."
              : "Files are processed by the configured application server."}
          </p>
        </div>
      </aside>
      <section
        className={classNames("content")}
        id={contentId}
        aria-label="AI File Inspector"
      >
        <header className={classNames("topline")}>
          <span>Writing & file analysis</span>
          <span className={classNames("model-status")}>
            {info
              ? info.model_ready
                ? "Gradient model ready"
                : "Model setup needed"
              : "Connecting to server…"}
          </span>
        </header>
        {history.length > 0 && (
          <div className={classNames("mobile-history")}>
            <label htmlFor={`${instanceId}-recent`}>Recent scans</label>
            <select
              id={`${instanceId}-recent`}
              value={job?.id || ""}
              onChange={(e) => {
                if (e.target.value) openJob(e.target.value);
              }}
            >
              <option value="">Open a saved report…</option>
              {history.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.files[0]?.name || "New scan"} · {h.status}
                </option>
              ))}
            </select>
          </div>
        )}
        {error && (
          <div role="alert" className={classNames("error")}>
            <strong>Something needs attention</strong>
            <p>{error}</p>
            <button
              className={classNames("text-button")}
              onClick={() => setError("")}
            >
              Dismiss
            </button>
          </div>
        )}
        {notice && (
          <p role="status" className={classNames("notice")}>
            {notice}
          </p>
        )}
        {page === "limits" ? (
          <section className={classNames("limits")}>
            <h1>File types & limits</h1>
            <p>Opening a file does not mean all its contents can be scored.</p>
            <div className={classNames("web-limits")}>
              <strong>Web portal upload limits</strong>
              <p>
                Up to 10 files per batch · 100 MB per file · 500 MB combined.
                Pasted text: up to 200,000 characters.
              </p>
            </div>
            <pre>{info?.limits_text || "Loading the guide…"}</pre>
            <section className={classNames("method")}>
              <h2>Can we improve the model weights?</h2>
              <p>
                Yes, through fine-tuning on correctly labelled human and AI
                examples. Random weight changes do not improve accuracy.
                Training must be followed by testing on separate examples that
                were not used to train or choose the model.
              </p>
              <p>
                This portal uses the verified Gradient model. No new weights
                have been trained for this interface.
              </p>
            </section>
          </section>
        ) : (
          <>
            <header className={classNames("page-heading")}>
              <h1>{job ? "Your file report" : "Understand your writing."}</h1>
              <p>
                {job
                  ? "Clear results, with the details you need to interpret them."
                  : "Check a document or paste text. Get a writing estimate you can understand."}
              </p>
            </header>
            {!job && (
              <div className={classNames("workspace")}>
                <form onSubmit={scan} className={classNames("upload-panel")}>
                  <div
                    className={classNames("mode-switch")}
                    role="group"
                    aria-label="Input method"
                  >
                    <button
                      type="button"
                      aria-pressed={mode === "files"}
                      onClick={() => setMode("files")}
                      disabled={busy}
                    >
                      Upload files
                    </button>
                    <button
                      type="button"
                      aria-pressed={mode === "text"}
                      onClick={() => setMode("text")}
                      disabled={busy}
                    >
                      Paste text
                    </button>
                  </div>
                  {mode === "files" ? (
                    <>
                      <div
                        className={classNames(
                          `dropzone ${dragging ? "dragging" : ""}`,
                        )}
                        onDragOver={(e) => {
                          e.preventDefault();
                          setDragging(true);
                        }}
                        onDragLeave={() => setDragging(false)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setDragging(false);
                          addFiles(e.dataTransfer.files);
                        }}
                      >
                        <Icon name="upload" width="32" height="32" />
                        <h2>Bring your files here</h2>
                        <p>
                          Drop files here, or choose them from your computer.
                        </p>
                        <div className={classNames("picker-actions")}>
                          <button
                            className={classNames("secondary")}
                            type="button"
                            disabled={!info || busy}
                            onClick={() => filePicker.current.click()}
                          >
                            Choose files
                          </button>
                          <button
                            className={classNames("text-button")}
                            type="button"
                            disabled={!info || busy}
                            onClick={() => folderPicker.current.click()}
                          >
                            Choose folder
                          </button>
                        </div>
                        <span className={classNames("small")}>
                          PDF, DOCX, text and pictures · up to 100 MB each
                        </span>
                      </div>
                      <input
                        ref={filePicker}
                        type="file"
                        multiple
                        accept={info?.extensions.join(",")}
                        hidden
                        onChange={(e) => {
                          addFiles(e.target.files);
                          e.target.value = "";
                        }}
                      />
                      <input
                        ref={folderPicker}
                        type="file"
                        multiple
                        webkitdirectory=""
                        hidden
                        onChange={(e) => {
                          addFiles(e.target.files, true);
                          e.target.value = "";
                        }}
                      />
                      {files.length > 0 && (
                        <ul className={classNames("selected-files")}>
                          {files.map((file, i) => (
                            <li key={`${file.name}-${i}`}>
                              <Icon name="file" />
                              <span>
                                {file.name}
                                <small>{formatSize(file.size)}</small>
                              </span>
                              <button
                                type="button"
                                className={classNames("icon-button")}
                                aria-label={`Remove ${file.name}`}
                                disabled={busy}
                                onClick={() =>
                                  setFiles(
                                    files.filter((_, index) => index !== i),
                                  )
                                }
                              >
                                <Icon name="close" />
                              </button>
                            </li>
                          ))}
                        </ul>
                      )}
                    </>
                  ) : (
                    <>
                      <label
                        className={classNames("textarea-label")}
                        htmlFor={`${instanceId}-writing`}
                      >
                        Your English writing
                      </label>
                      <textarea
                        id={`${instanceId}-writing`}
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        maxLength={200000}
                        placeholder="Paste at least 100 words of English prose…"
                        disabled={busy}
                      />
                      <p className={classNames("input-count")}>
                        {text.trim() ? text.trim().split(/\s+/).length : 0}{" "}
                        words (approx.) · {text.length.toLocaleString()} /
                        200,000 characters
                      </p>
                    </>
                  )}
                  <div className={classNames("submit-row")}>
                    <button
                      type="submit"
                      className={classNames("primary")}
                      disabled={
                        !info ||
                        busy ||
                        (mode === "files" ? files.length === 0 : !text.trim())
                      }
                    >
                      {sending ? "Uploading…" : "Check writing"}
                      <Icon name="check" />
                    </button>
                    <span className={classNames("small")}>
                      At least 100 English words for a writing estimate.
                    </span>
                  </div>
                </form>
                <aside className={classNames("explain")}>
                  <h2>A percentage with context.</h2>
                  <p>
                    The report shows the share of checked text in sections
                    flagged as AI-like, human-like or uncertain.
                  </p>
                  <p>
                    It is an estimate of writing patterns—not a measurement of
                    who wrote each word.
                  </p>
                  <div className={classNames("explain-rule")} />
                  <h3>Know what was checked</h3>
                  <p>
                    Long documents may be sampled. You will see the coverage
                    next to your result.
                  </p>
                  <h3>Pictures work differently</h3>
                  <p>
                    Image uploads get file and pattern checks, not an AI-image
                    verdict.
                  </p>
                  <button
                    className={classNames("text-button")}
                    onClick={() => setPage("limits")}
                  >
                    Read the file limits
                  </button>
                </aside>
              </div>
            )}
            {job && (
              <section aria-label="Scan report">
                <div
                  className={classNames(
                    `scan-progress ${active(job) ? "working" : ""}`,
                  )}
                  role="status"
                >
                  <div>
                    <strong>
                      {job.status === "complete"
                        ? "Scan finished"
                        : job.status === "failed"
                          ? "Scan stopped"
                          : job.status === "queued"
                            ? "Your scan is queued"
                            : "Checking your files"}
                    </strong>
                    <p>{job.error || job.progress}</p>
                    {active(job) && (
                      <p className={classNames("small")}>
                        The first file may take longer while the model loads.
                        You can leave this page open.
                      </p>
                    )}
                  </div>
                  {active(job) && <progress aria-label="Scanning" />}
                </div>
                {job.results?.map((r, i) => (
                  <FileResult
                    key={`${job.id}-${i}`}
                    result={r}
                    jobId={job.id}
                    api={api}
                  />
                ))}
                {!active(job) && (
                  <div className={classNames("report-actions")}>
                    <button className={classNames("primary")} onClick={newScan}>
                      <Icon name="plus" />
                      Check another file
                    </button>
                    <a
                      className={classNames("secondary")}
                      href={api.url(`jobs/${job.id}/report/`)}
                      download
                    >
                      Download report JSON
                    </a>
                    <button
                      className={classNames("text-button danger")}
                      onClick={removeReport}
                    >
                      Delete this scan
                    </button>
                  </div>
                )}
              </section>
            )}
            <footer>
              AI estimates can be wrong. Review the original writing before
              making a decision.
            </footer>
          </>
        )}
      </section>
    </div>
  );
}
