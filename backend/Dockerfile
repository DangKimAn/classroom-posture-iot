FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
RUN useradd --create-home app
USER app
CMD ["python", "-m", "api"]
