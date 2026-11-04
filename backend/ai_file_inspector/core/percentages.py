"""Describe model signals without presenting them as proven authorship."""

import math


def percentage_breakdown(detection):
    if not detection or detection.get("status") != "estimated":
        return None
    passages = detection.get("passages", [])
    total = sum(p.get("tokens", 0) for p in passages)
    if total <= 0:
        return None
    counts = {"ai_like": 0, "human_like": 0, "uncertain": 0}
    for p in passages:
        score = p["ai_pattern_score"]
        tokens = p["tokens"]
        if not math.isfinite(score) or tokens <= 0:
            raise ValueError("Invalid passage result")
        key = p.get("signal_band") or (
            "ai_like" if score >= 80 else "human_like" if score <= 20 else "uncertain"
        )
        if key not in counts:
            raise ValueError("Invalid signal band")
        counts[key] += tokens
    # Largest remainder gives whole percentages that add up to exactly 100.
    exact = {k: 100 * v / total for k, v in counts.items()}
    rounded = {k: math.floor(v) for k, v in exact.items()}
    for key in sorted(exact, key=lambda k: exact[k] - rounded[k], reverse=True)[
        : 100 - sum(rounded.values())
    ]:
        rounded[key] += 1
    return {
        **rounded,
        "checked_tokens": total,
        "sampled": detection.get("coverage") == "sampled",
        "meaning": "Share of checked tokens in sections flagged AI-like, human-like or uncertain. This is not a measured percentage of AI-authored words.",
    }
