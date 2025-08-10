FROM python:3.11-slim
WORKDIR /app

# if you kept requirements-api.txt:
COPY requirements-api.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY artifacts/ /app/artifacts/

ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
