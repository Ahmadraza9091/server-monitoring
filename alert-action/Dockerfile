FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY dashboard.html .
COPY login.html .
COPY init.sql .
COPY migrate_schema.py .
COPY seed_admin.py .
COPY migrate_json_to_db.py .

# Expose web dashboard / webhook port
EXPOSE 5000

# Start app
CMD ["python", "app.py"]

