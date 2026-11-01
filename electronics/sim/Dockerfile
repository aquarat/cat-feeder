FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends ngspice \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1
