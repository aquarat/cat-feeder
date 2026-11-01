FROM python:3.12-trixie
RUN apt-get update && apt-get install -y --no-install-recommends kicad kicad-footprints kicad-symbols python3-numpy python3-pil default-jre-headless ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /work
