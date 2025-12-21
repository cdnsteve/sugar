FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/roboticforce/sugar"
LABEL org.opencontainers.image.description="Sugar Issue Responder - AI-powered GitHub issue assistant"
LABEL org.opencontainers.image.licenses="MIT"

# Install git and gh CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the sugar package
COPY sugar/ ./sugar/
COPY pyproject.toml .

# Install sugar
RUN pip install --no-cache-dir -e .

# Copy the entrypoint
COPY action/entrypoint.py /entrypoint.py

# Set the entrypoint
ENTRYPOINT ["python", "/entrypoint.py"]
