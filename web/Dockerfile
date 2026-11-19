FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    BACKEND_URL=http://api:8000

WORKDIR /app
COPY . ./web

RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8080
CMD ["python", "web/app_web.py"]
