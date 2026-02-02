# Issue Summarizer

Small utility to generate short summaries and extract action items from GitHub issue payloads.

Usage (CLI):

```bash
python tools/issue-summarizer/summarizer.py path/to/issue.json
```

Optional LLM integration: set `OPENAI_API_KEY` and `OPENAI_MODEL` to enable the `--llm` flag.
