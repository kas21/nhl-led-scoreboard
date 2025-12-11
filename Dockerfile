# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.13-slim-trixie AS builder

WORKDIR /app 
# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1


# Install pip requirements
COPY requirements-docker.txt requirements.txt
RUN python -m pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt && rm -rf /root/.cache/pip

FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install -y \
     libcairo2 \
     && rm -rf /var/lib/apt/lists/* \
     && apt-get clean

WORKDIR /app
COPY . /app
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN python -m pip install --no-cache /wheels/*

# Add the entrypoint script and make it executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Creates a non-root user
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Ensure local user bin is in PATH so the app can find the new plugin modules
ENV PATH="/home/appuser/.local/bin:${PATH}"

EXPOSE 8888

# Set the new entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]