# D34 simulation image: ngspice + Python numerics/plotting from Debian bookworm.
# Built once (needs network); every simulation run uses --network none.
FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ngspice python3 python3-numpy python3-matplotlib python3-scipy \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg MPLCONFIGDIR=/tmp
WORKDIR /work
