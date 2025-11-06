# Use Python 3.13 as the base image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Add user
RUN useradd -ms /bin/bash demux-sapio-user

# Install uv system-wide and create a dedicated virtual environment at /opt/venv
# Dependencies will be installed into /opt/venv so /app stays clean.
WORKDIR /opt
COPY pyproject.toml uv.lock .
RUN pip install --no-cache-dir uv==0.9.0 && \
    uv sync --no-cache --all-groups && \
    chown -R demux-sapio-user:demux-sapio-user /opt/.venv

ENV VIRTUAL_ENV=/opt/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Switch to non-root user
USER demux-sapio-user

WORKDIR /app
# Copy the rest of the project
COPY . /app
ENV PYTHONPATH=/app

ENTRYPOINT ["demux-sapio-watcher"]
