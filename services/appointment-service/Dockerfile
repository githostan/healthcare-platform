
# Base image: use official Python runtime. slim keeps image smaller.
FROM python:3.12-slim

# Set the working directory inside the container: all future commands run inside /app (clean, predictable)
WORKDIR /app

# Environment settings: prevents .pyc files & ensures logs flush immediately (important for Docker/K8s logging)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Upgrade pip inside image. --no-cache-dir keeps image smaller.
RUN pip install --no-cache-dir --upgrade pip

# Copy only dependencies file first (enables Docker cache).
COPY requirements.txt .

# Install dependencies into the container’s Python site-packages.
RUN pip install --no-cache-dir -r requirements.txt

# Documentation: expose the port the app listens on (inside container), as this container expects traffic on 8000
EXPOSE 8000

# Create a non-root user:
# Security hardening / best practice: containers should not run as root; create a dedicated non-root user for the app
# Run the app with least privilege so the app does not run as root inside the container.
RUN useradd -m appuser

# Copy application code into the image (and set correct ownership)
COPY --chown=appuser:appuser app ./app

# Copy Demo UI assets (templates + static)
COPY --chown=appuser:appuser templates ./templates
COPY --chown=appuser:appuser static ./static

# Run as non-root
USER appuser

# Default command to run the app / default process when container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
