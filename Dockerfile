FROM python:3.11-slim

WORKDIR /app
COPY requirements-api.txt requirements.txt* pyproject.toml* poetry.lock* /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir fastapi uvicorn[standard] pydantic aiofiles

COPY . /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

# Use the main app with dynamic port from environment
CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
