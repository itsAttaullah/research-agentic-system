# Playwright base image ships Chromium + system deps, which the Website Reader
# and HTML->PDF report export require. Pin the version to match pyproject.
FROM mcr.microsoft.com/playwright/python:v1.46.0-jammy

WORKDIR /app

# Install dependencies first for layer caching.
COPY pyproject.toml README.md ./
COPY sra ./sra
RUN pip install --no-cache-dir .

# Non-root runtime user; data dir for SQLite/DuckDB/checkpoints.
RUN useradd --create-home sra && mkdir -p /app/data && chown -R sra:sra /app
USER sra

ENV SRA_DATA_DIR=/app/data
EXPOSE 8000

CMD ["uvicorn", "sra.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
