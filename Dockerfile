# Use an official Python runtime as a parent image
FROM python:3.11.4-alpine AS builder

# Set work directory
WORKDIR /usr/src/app

# Install system dependencies
RUN apk add --no-cache \
        curl \
        gcc \
        libc-dev \
        linux-headers 

# Copy requirements.txt and install requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Use a clean base image for the final image
FROM python:3.11.4-alpine

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV DATABASE_PATH=/usr/src/app/db/

# Set work directory
WORKDIR /usr/src/app

# Copy the installed packages from the builder image
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy the application code
COPY . .

# Run the command to start uWSGI
CMD python3 main.py