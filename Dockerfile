FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8080

CMD ["flet", "run", "--web", "--host", "*", "--port", "8080", "main.py"]
