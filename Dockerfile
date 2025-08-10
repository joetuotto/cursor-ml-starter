FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app + artifacts (schema)
COPY app/ ./app/
COPY artifacts/ /app/artifacts/

# optional: let Cloud Run know the port
ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
