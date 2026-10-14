ARG BUILD_FROM
FROM $BUILD_FROM

# Install dependencies
RUN apk add --no-cache python3 py3-pip

# Copy application files
COPY rootfs /

# Create virtual environment and install dependencies
RUN python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r /app/requirements.txt
