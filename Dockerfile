# Dockerfile for MailMind
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create persistent storage directories
RUN mkdir -p data logs attachments

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["python", "mailmind.py"]
