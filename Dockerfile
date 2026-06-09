# Use the official Python lightweight image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Copy dependency requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend server and the website HTML page
COPY main.py .
COPY Autonomiqa_Website_with_Contact.html .

EXPOSE 8080

# Run uvicorn on port 8080 (Cloud Run default)
CMD uvicorn main:app --host 0.0.0.0 --port 8080
