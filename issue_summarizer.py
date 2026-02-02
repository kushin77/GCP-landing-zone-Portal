"""Compatibility shim for tests.

The working folder uses a hyphen in the tools path (issue-summarizer) which
cannot be imported as a package name. This shim exposes `summarizer` under
the importable module name `issue_summarizer` so tests can run.
"""
from __future__ import annotations

import os
import sys

_pkg_path = os.path.join(os.path.dirname(__file__), "tools", "issue-summarizer")
if _pkg_path not in sys.path:
    sys.path.insert(0, _pkg_path)

try:
    import summarizer as _summ  # type: ignore
except Exception:  # pragma: no cover - import shim for tests
    _summ = None

summarizer = _summ
