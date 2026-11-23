# Single lightweight multi-arch Python 3.11 image for Prisma SASE 5G Manager
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and generating .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CONFIG_DIR=/app/config \
    PORT=8000

WORKDIR /app

# Install system dependencies if required (including docker-cli for 1-click ephemeral upgrades)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    openssh-client \
    iproute2 \
    iputils-ping \
    libsctp1 \
    ca-certificates \
    && ARCH=$(dpkg --print-architecture) \
    && DOCKER_ARCH=$([ "$ARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") \
    && curl -fsSL "https://download.docker.com/linux/static/stable/${DOCKER_ARCH}/docker-27.3.1.tgz" | tar xz -C /usr/local/bin --strip-components=1 docker/docker \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /etc/iproute2 \
    && cp /usr/share/iproute2/rt_tables /etc/iproute2/rt_tables

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and prepare persistent directories
ARG APP_VERSION=""
ARG GIT_COMMIT=""
ENV APP_VERSION=${APP_VERSION} \
    GIT_COMMIT=${GIT_COMMIT}

RUN mkdir -p /app/config /app/static
COPY src/ /app/src/
COPY templates/ /app/templates/
COPY static/ /app/static/
COPY app.py /app/app.py
COPY agent_app.py /app/agent_app.py
COPY manage_5g.py /app/manage_5g.py
COPY test_lifecycle.py /app/test_lifecycle.py
COPY CHANGELOG.md /app/CHANGELOG.md
COPY VERSION /app/VERSION
COPY .env.example /app/.env.example

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose ports
EXPOSE 8000 8080 8081

# Entrypoint dispatcher
ENTRYPOINT ["/app/entrypoint.sh"]

