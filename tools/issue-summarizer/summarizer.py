"""Simple Issue Summarizer and Action Item Extractor.

This module provides a small CLI-friendly summarizer which uses a
lightweight heuristic by default and exposes a hook `call_llm` for
future LLM integrations (OpenAI, etc.).

Design goals:
- Minimal runtime dependencies
- Full type hints
- Testable deterministic heuristics when no API key is provided
"""
from __future__ import annotations

from typing import Dict, List
import argparse
import json
import re
import os


def extract_summary(issue: Dict) -> str:
    """Create a short summary for an issue dict.

    Falls back to the issue title + the first sentence of the body if
    no LLM is configured.
    """
    title = issue.get("title", "(no title)")
    body = issue.get("body") or issue.get("description") or ""

    # strip markdown and collapse whitespace
    text = re.sub(r"\s+", " ", re.sub(r"[#>*`\[\]]", "", body)).strip()
    first_sentence = (
        re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0] if text else ""
    )

    return f"{title} — {first_sentence}" if first_sentence else title


def extract_action_items(issue: Dict) -> List[str]:
    """Extract bullet-like action items from the issue body using heuristics.

    Looks for lines that start with verbs, TODO, or list markers.
    """
    body = issue.get("body") or issue.get("description") or ""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    items: List[str] = []

    # common bullet markers often indicate action items
    for ln in lines:
        if ln.lower().startswith("todo") or ln.lower().startswith("action"):
            items.append(ln)
            continue
        if re.match(r"^[\-\*\d\.]+\s+", ln):
            # strip marker
            items.append(re.sub(r"^[\-\*\d\.]+\s+", "", ln))
            continue
        # short imperative lines that begin with a verb
        if re.match(r"^[A-Z][a-z]+\b.*", ln) and len(ln.split()) < 12:
            # heuristic: treat as an action if starts with a verb-ish token
            items.append(ln)

    # de-duplicate while preserving order
    seen = set()
    out = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def call_llm(prompt: str) -> str:
    """Placeholder for LLM integration.

    If `OPENAI_API_KEY` is set and `openai` is installed this function
    can be extended to call the model. For now it raises when not
    available so callers can fallback to heuristic behavior.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("No LLM API key configured")

    try:
        import openai

        openai.api_key = api_key
        resp = openai.ChatCompletion.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # pragma: no cover - depends on external service
        raise RuntimeError("LLM call failed") from exc


def summarize_issue(issue: Dict, use_llm: bool = False) -> Dict[str, object]:
    """Return a summary and action-items for an issue dict."""
    if use_llm:
        prompt = f"Summarize the following GitHub issue and list action items:\n\n{issue.get('title')}\n{issue.get('body','')}"
        try:
            llm_out = call_llm(prompt)
            # simple split heuristic: LLM output may contain action items
            parts = llm_out.split("\n\n", 1)
            summary = parts[0]
            actions = parts[1].splitlines() if len(parts) > 1 else []
            return {"summary": summary.strip(), "action_items": [a.strip() for a in actions if a.strip()]}
        except RuntimeError:
            # fallback to heuristic
            pass

    return {"summary": extract_summary(issue), "action_items": extract_action_items(issue)}


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(description="Issue Summarizer CLI")
    parser.add_argument("issue_file", help="Path to issue JSON file")
    parser.add_argument("--llm", action="store_true", help="Use configured LLM when available")
    args = parser.parse_args()

    with open(args.issue_file, "r", encoding="utf-8") as fh:
        issue = json.load(fh)

    out = summarize_issue(issue, use_llm=args.llm)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
