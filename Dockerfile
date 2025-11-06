# Use Python 3.13 as the base image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Add user
RUN useradd -ms /bin/bash demux-sapio-user

# Install system dependencies (if any) and clean apt cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv system-wide and create a dedicated virtual environment at /opt/venv
# Dependencies will be installed into /opt/venv so /app stays clean.
WORKDIR /opt
COPY pyproject.toml uv.lock .
RUN pip install --no-cache-dir uv==0.9.0 && \
    uv sync --no-cache --all-groups

ENV VIRTUAL_ENV=/opt/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN chown -R demux-sapio-user:demux-sapio-user /opt/.venv
# Switch to non-root user
USER demux-sapio-user

WORKDIR /app
# Copy the rest of the project
COPY . /app
ENV PYTHONPATH=/app

ENTRYPOINT ["demux-sapio-watcher"]
