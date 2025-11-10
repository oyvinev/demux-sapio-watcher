# demux-sapio-watcher

A CLI tool that monitors file systems for BCLConvert output folders, parses sequencing data, and updates corresponding Sapio SequencingFile records with FASTQ file paths.

## Overview

This tool scans specified directories for BCLConvert output folders, extracts sequencing metadata, and synchronizes the information with a Sapio LIMS system. It's designed to automate the process of updating Sapio records when new sequencing files become available.

## Features

- **BCLConvert folder detection**: Automatically discovers folders containing BCLConvert outputs
- **FASTQ file parsing**: Extracts sample information from FASTQ file names and metadata
- **Sapio integration**: Updates SequencingFile records in Sapio with file paths and metadata
- **Flexible filtering**: Include/exclude patterns for fine-grained control over which folders to process
- **Dry run mode**: Test operations without making actual changes to Sapio
- **Docker support**: Containerized deployment

## Installation

### Using Docker (Recommended)

Build the image:
```bash
docker build -t demux-sapio-watcher .
```

### Local Development

Install dependencies using uv:
```bash
pip install uv
uv sync --all-groups
```

## Usage

### Command Line Interface

```bash
# Basic usage with dry run
demux-sapio-watcher /path/to/sequencing/data --dry-run

# With include/exclude patterns
demux-sapio-watcher /path/to/data \
    --include-patterns "2024*" "2023-12*" \
    --exclude-patterns "*test*" "*backup*"

# Production usage with authentication
demux-sapio-watcher /path/to/data \
    --api-token YOUR_API_TOKEN \
    --url-base https://your-sapio-instance.com \
    --app-key YOUR_APP_KEY
```

### Docker Usage

```bash
# Basic usage with mounted volumes
docker run -v /path/to/data:/data demux-sapio-watcher /data --dry-run

# Production usage with environment variables
docker run \
    -e SAPIO_API_TOKEN=your_token \
    -e SAPIO_URL_BASE=https://your-sapio-instance.com \
    -e SAPIO_APP_KEY=your_app_key \
    -v /path/to/data:/data \
    demux-sapio-watcher /data
```

## Configuration

### Environment Variables

The following environment variables can be used instead of command-line options:

- `SAPIO_API_TOKEN` - Sapio API authentication token
- `SAPIO_URL_BASE` - Base URL for your Sapio instance
- `SAPIO_APP_KEY` - Sapio application key
- `SAPIO_USERNAME` - Sapio username (alternative to API token)
- `SAPIO_PASSWORD` - Sapio password (alternative to API token)

### Command Line Options

```
usage: fastq-watcher [-h] [--exclude-patterns EXCLUDE_PATTERNS [EXCLUDE_PATTERNS ...]]
                     [--include-patterns INCLUDE_PATTERNS [INCLUDE_PATTERNS ...]] [--dry-run]
                     [--api-token API_TOKEN] [--url-base URL_BASE] [--app-key APP_KEY]
                     [--username USERNAME] [--password PASSWORD]
                     [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--no-sapio]
                     root_paths [root_paths ...]

positional arguments:
  root_paths            root paths to search

options:
  -h, --help            show this help message and exit
  --exclude-patterns EXCLUDE_PATTERNS [EXCLUDE_PATTERNS ...]
                        patterns to exclude
  --include-patterns INCLUDE_PATTERNS [INCLUDE_PATTERNS ...]
                        patterns to include
  --dry-run             Don't update Sapio, just log actions
  --api-token API_TOKEN
                        Sapio API token (defaults to SAPIO_API_TOKEN env)
  --url-base URL_BASE   Sapio base URL (defaults to SAPIO_URL_BASE env)
  --app-key APP_KEY     Sapio app key (defaults to SAPIO_APP_KEY env)
  --username USERNAME   Sapio username (defaults to SAPIO_USERNAME env)
  --password PASSWORD   Sapio password (defaults to SAPIO_PASSWORD env)
  --log-level, -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Set log level
  --no-sapio            Do not call Sapio API at all
```

## Development

### Running Tests

```bash
# Install development dependencies
uv sync --all-groups

# Run tests
pytest

```
