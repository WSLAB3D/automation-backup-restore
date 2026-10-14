ARG BUILD_FROM
FROM $BUILD_FROM

# Install dependencies
RUN apk add --no-cache python3 py3-pip

# Copy application files
COPY rootfs /
RUN pip3 install -r /app/requirements.txt
