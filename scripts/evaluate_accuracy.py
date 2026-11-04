"""Offline reference check. Input JSONL: id, text, label (human/ai), domain.
Only use known-origin labels. Reports contain scores and IDs, not input text.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def summarize(rows):
    counts = Counter(r["outcome"] for r in rows)
    human = sum(r["expected"] == "human" for r in rows)
    ai = len(rows) - human
    decided = counts["correct"] + counts["human_flagged_ai"] + counts["ai_called_human"]

    def percent(n, d):
        return round(100 * n / d, 1) if d else None

    return dict(
        total=len(rows),
        human_examples=human,
        ai_examples=ai,
        correct=counts["correct"],
        human_flagged_ai=counts["human_flagged_ai"],
        ai_called_human=counts["ai_called_human"],
        uncertain=counts["uncertain"],
        not_checked=counts["not_checked"],
        errors=counts["error"],
        human_false_alarm_percent=percent(counts["human_flagged_ai"], human),
        ai_called_human_percent=percent(counts["ai_called_human"], ai),
        clear_answer_percent=percent(decided, len(rows)),
        correct_among_clear_answers_percent=percent(counts["correct"], decided),
    )


def load_examples(path):
    examples, ids, hashes = [], set(), set()
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        if (
            row.get("label") not in ("human", "ai")
            or not isinstance(row.get("text"), str)
            or not row["text"].strip()
        ):
            raise ValueError(f"Line {line_number}: provide text and a human/ai label.")
        if not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError(f"Line {line_number}: provide a unique string id.")
        digest = hashlib.sha256(" ".join(row["text"].split()).encode()).hexdigest()
        if row["id"] in ids or digest in hashes:
            raise ValueError(
                f"Line {line_number}: duplicate id or text would bias the results."
            )
        ids.add(row["id"])
        hashes.add(digest)
        examples.append(row)
    if not examples:
        raise ValueError("No examples found.")
    return examples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("examples", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    examples = load_examples(args.examples)
    from ai_file_inspector.core import detector

    rows = []
    for i, example in enumerate(examples, 1):
        result = detector.analyze(example["text"])
        label = result.get("label", "")
        prediction = (
            "ai"
            if label == "Leans AI-generated"
            else "human"
            if label == "Leans human-written"
            else "uncertain"
            if result["status"] == "estimated"
            else result["status"]
        )
        outcome = (
            "correct"
            if prediction == example["label"]
            else "human_flagged_ai"
            if prediction == "ai"
            else "ai_called_human"
            if prediction == "human"
            else prediction
        )
        rows.append(
            dict(
                id=example["id"],
                domain=example.get("domain", "unspecified"),
                expected=example["label"],
                prediction=prediction,
                outcome=outcome,
                score=result.get("ai_pattern_score"),
                reason=result.get("reason"),
            )
        )
        print(f"{i}/{len(examples)} {example['id']}: {outcome}", flush=True)
    report = dict(
        model=detector.MODEL_NAME,
        model_sha256=detector.MODEL_SHA,
        detector_sha256=hashlib.sha256(
            (args.app / "ai_detector.py").read_bytes()
        ).hexdigest(),
        dataset_sha256=hashlib.sha256(args.examples.read_bytes()).hexdigest(),
        limitation="Reference check only. Training overlap, sample selection and sample size affect results. Do not claim general accuracy from this report. Uncertain and skipped results are not correct answers.",
        overall=summarize(rows),
        by_domain={
            d: summarize([r for r in rows if r["domain"] == d])
            for d in sorted({r["domain"] for r in rows})
        },
        rows=rows,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["overall"], indent=2))


if __name__ == "__main__":
    from bootstrap import configure

    configure()
    main()
