import Icon from "./Icon.jsx";
import { classNames } from "../styles/classNames.js";

const categories = [
  { key: "human_like", label: "Human", color: "human" },
  { key: "ai_like", label: "AI", color: "ai" },
  { key: "uncertain", label: "Uncertain", color: "unknown" },
];
export default function FileResult({ result, jobId, api }) {
  const detection = result.text?.ai_detection;
  const share = result.breakdown;
  const estimated = detection?.status === "estimated";
  const label = estimated
    ? detection.label === "Leans AI-generated"
      ? "Looks AI-written"
      : detection.label === "Leans human-written"
        ? "Looks human-written"
        : "Not sure"
    : "AI writing not checked";
  const explanation = estimated
    ? label === "Not sure"
      ? "The model cannot give a clear answer. Some writing patterns are ambiguous or different sections disagree."
      : label === "Looks AI-written"
        ? "The writing resembles AI examples. This does not prove that AI wrote it."
        : "The writing resembles human examples. The detector can still miss AI use."
    : detection?.reason ||
      (result.images?.length
        ? "Pictures receive file and pattern checks. This tool does not judge whether an image was AI-generated."
        : result.error || "No readable prose was available.");
  const issues = result.issues || [];
  return (
    <article
      className={classNames("result")}
      aria-label={`Result for ${result.file}`}
    >
      <header className={classNames("result-heading")}>
        <div className={classNames("file-title")}>
          <Icon name="file" />
          <h2>{result.file}</h2>
        </div>
        <span
          className={classNames(
            `status ${result.status === "complete" ? "good" : "attention"}`,
          )}
        >
          {result.status === "failed"
            ? "Could not read file"
            : result.status === "partial"
              ? "Partly checked"
              : "Checks finished"}
        </span>
      </header>
      {!share && (
        <div className={classNames("verdict")}>
          <h3>{label}</h3>
          <p>{explanation}</p>
        </div>
      )}
      {share && (
        <section
          className={classNames("share")}
          aria-label="Percentage of checked text"
        >
          <h3 className={classNames("share-heading")}>
            Estimated content breakdown
          </h3>
          <dl className={classNames("share-values")}>
            {categories.map(({ key, label, color }) => (
              <div key={key} className={classNames("share-value")}>
                <dt>
                  <i className={classNames(color)} aria-hidden="true" />
                  {label}
                </dt>
                <dd className={classNames("percentage")}>{share[key]}%</dd>
              </div>
            ))}
          </dl>
          <div
            className={classNames("share-bar")}
            role="img"
            aria-label={`Estimated content: ${share.human_like}% Human, ${share.ai_like}% AI, ${share.uncertain}% Uncertain`}
          >
            <span
              className={classNames("human")}
              style={{
                width: `${share.human_like}%`,
              }}
            />
            <span
              className={classNames("ai")}
              style={{
                width: `${share.ai_like}%`,
              }}
            />
            <span
              className={classNames("unknown")}
              style={{
                width: `${share.uncertain}%`,
              }}
            />
          </div>
          <p className={classNames("small")}>
            Estimates for the checked text, based on section length and writing
            patterns. They do not prove who wrote the text. Uncertain means the
            model could not decide.
          </p>
        </section>
      )}
      {estimated && (
        <div
          className={classNames(
            `coverage ${share?.sampled ? "attention" : ""}`,
          )}
        >
          <Icon name="info" />
          <div>
            <strong>
              {share?.sampled
                ? "Only part of this document was scored."
                : "All extracted eligible text was scored."}
            </strong>
            <p>
              Checked {detection.passages_checked} of {detection.total_passages}{" "}
              sections · {detection.words_in_checked_text?.toLocaleString()}{" "}
              words in the considered text.
            </p>
            {detection.notes?.slice(1).map((note, i) => (
              <p key={i}>{note}</p>
            ))}
          </div>
        </div>
      )}
      {result.pages_attempted != null && (
        <p className={classNames("small")}>
          PDF: attempted all {result.pages_attempted} of {result.page_count}{" "}
          pages. Readable text was found on {result.pages_with_readable_text}{" "}
          pages. Blank pages and pages needing OCR do not add readable text.
        </p>
      )}
      {issues.length > 0 && (
        <div className={classNames("issues")}>
          <strong>What could not be fully checked</strong>
          <ul>
            {issues.map((issue, i) => (
              <li key={i}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
      {result.text && (
        <section className={classNames("file-checks")}>
          <h3>Other file checks</h3>
          <dl>
            <div>
              <dt>Unusual characters</dt>
              <dd>{result.text.unusual_character_count ?? 0}</dd>
            </div>
            <div>
              <dt>Mixed-alphabet words</dt>
              <dd>{result.text.mixed_alphabet_word_count ?? 0}</dd>
            </div>
          </dl>
          <p className={classNames("small")}>
            These clues can have ordinary explanations. They do not prove AI
            use.
          </p>
        </section>
      )}
      {estimated && (
        <details>
          <summary>See section scores and model details</summary>
          <p className={classNames("small")}>
            {detection.model}. Model signal: {detection.ai_pattern_score} / 100.
            This signal is not a probability of authorship.
          </p>
          <div className={classNames("table-scroll")}>
            <table>
              <thead>
                <tr>
                  <th>Section</th>
                  <th>AI-pattern score</th>
                  <th>Beginning of text</th>
                </tr>
              </thead>
              <tbody>
                {detection.passages.map((p) => (
                  <tr key={p.passage_number}>
                    <td>{p.passage_number}</td>
                    <td>{p.ai_pattern_score} / 100</td>
                    <td>{p.text_excerpt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      {result.images?.length > 0 && (
        <details className={classNames("image-details")}>
          <summary>
            See image checks · {result.images.length} image
            {result.images.length === 1 ? "" : "s"}
          </summary>
          <p className={classNames("small")}>
            These are exploratory pattern views, not evidence of an AI
            watermark.
          </p>
          {result.images.map((picture, i) => (
            <section key={i} className={classNames("image-group")}>
              <h4>{picture.source}</h4>
              {picture.analysis_note && <p>{picture.analysis_note}</p>}
              {picture.frame_note && <p>{picture.frame_note}</p>}
              <div className={classNames("pictures")}>
                {picture.visuals.map((v, k) => (
                  <figure key={k}>
                    <img
                      loading="lazy"
                      alt={v.caption}
                      src={api.url(
                        `jobs/${jobId}/assets/${encodeURIComponent(v.file.split("/").pop())}`,
                      )}
                    />
                    <figcaption>{v.caption}</figcaption>
                  </figure>
                ))}
              </div>
            </section>
          ))}
        </details>
      )}
      <details>
        <summary>See file metadata and technical details</summary>
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </details>
    </article>
  );
}
