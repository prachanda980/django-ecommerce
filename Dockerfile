FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories for static files and media
RUN mkdir -p /app/static /app/media

# Collect static files
RUN python manage.py collectstatic --noinput

# Set permissions
RUN chmod +x /app/manage.py

# Expose ports
EXPOSE 8000 8001

# Run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]