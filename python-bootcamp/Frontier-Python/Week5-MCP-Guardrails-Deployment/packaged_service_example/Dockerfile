# Dockerfile — packaged_service_example
# Week 5 — Packaging for Deployment
#
# Not a Python file, but the immediate, essential companion to it: this is what turns
# main.py from "runs on my machine" into "runs the same way everywhere," which is the
# actual bar Week 5/6 hold every capstone to.
#
# Build:  docker build -t frontier-service-example .
# Run:    docker run --env-file .env -p 8000:8000 frontier-service-example

FROM python:3.11-slim

WORKDIR /app

# Copy dependency list first so Docker can cache this layer separately from code changes —
# code changes shouldn't force a full dependency reinstall.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY . .

# Never bake secrets into the image — they arrive at runtime via --env-file or an
# orchestrator's secrets manager, per Week 5's "never hardcode API keys" guidance.
ENV PORT=8000

EXPOSE 8000

CMD ["python3", "main.py"]
