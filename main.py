"""Entry point shim for the fastq watcher CLI.

This module keeps the workspace's original `main.py` but wires it to the
`fastq_watcher` package CLI implemented in this project.
"""

from __future__ import annotations

import sys

from fastq_watcher.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
	"""Run the CLI.

	Returns an exit code suitable for `sys.exit`.
	"""
	if argv is None:
		argv = sys.argv[1:]
	try:
		cli_main(argv)
		return 0
	except Exception as exc:  # pragma: no cover - top-level guard
		print(f"Error: {exc}", file=sys.stderr)
		return 2


if __name__ == "__main__":
	raise SystemExit(main())

