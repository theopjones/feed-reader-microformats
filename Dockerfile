# Use an official Python runtime as a parent image
FROM python

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV DATABASE_PATH=/usr/src/app/db/

# Set work directory
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gcc \
        default-libmysqlclient-dev \
        bash \
        && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Run the command to start uWSGI
CMD python3 main.py
