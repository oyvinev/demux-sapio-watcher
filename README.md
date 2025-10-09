fastq-watcher
==============

Small CLI that finds paired FASTQ files named <prefix>_R1.fastq and
<prefix>_R2.fastq, extracts a UUID from the prefix, and updates the
corresponding Sapio SequencingFile record fields `read1_fastq` and
`read2_fastq`.


Usage (dry run):

    python -m main --dry-run "path/**/_R1.fastq"

Installing dependencies in Docker

This project prefers installing runtime dependencies in the `Dockerfile`.
The included `Dockerfile` already installs `sapiopylib`.

Run tests

If you want to run tests locally, install pytest in your development environment:

    pip install pytest
    pytest -q

Environment variables

The CLI reads Sapio connection defaults from environment variables. The
following environment variable names are supported (and are used when the
corresponding CLI option is not provided):

- `SAPIO_API_TOKEN`
- `SAPIO_URL_BASE`
- `SAPIO_APP_KEY`
- `SAPIO_USERNAME`
- `SAPIO_PASSWORD`

Or add pytest to the Dockerfile for running tests inside the container.
