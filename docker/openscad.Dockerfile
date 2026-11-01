# Headless OpenSCAD for this project's CAD scripts (scripts/openscad.sh).
#
# Builds the public fork github.com/aquarat/openscad at a pinned commit. The
# fork adds the experimental `geometry-metrics` feature (bbox()/centroid()/
# sharp_edges()) that the clearance and access reports use; ordinary part
# exports also work with it. Build from the repository root:
#
#   docker build -t cat-feeder-openscad -f docker/openscad.Dockerfile docker
#
# The build compiles CGAL-heavy code: JOBS=2 takes 20-40 min but fits in a
# ~8 GB Docker VM. Raise it with --build-arg JOBS=N when RAM allows.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git ca-certificates pkg-config bison flex gettext \
    libeigen3-dev \
    libboost-filesystem-dev libboost-program-options-dev \
    libboost-regex-dev libboost-system-dev \
    libcgal-dev libgmp-dev libmpfr-dev \
    libglib2.0-dev libfontconfig-dev libfreetype-dev libharfbuzz-dev \
    libzip-dev libxml2-dev libdouble-conversion-dev libtbb-dev libssl-dev \
    libcairo2-dev \
    libglew-dev libegl-dev libgl-dev libglx-dev libx11-dev \
    libgl1-mesa-dri xvfb xauth \
    fonts-liberation \
  && rm -rf /var/lib/apt/lists/*

ARG OPENSCAD_REPO=https://github.com/aquarat/openscad.git
ARG OPENSCAD_COMMIT=12b187123519cd9050ce37341aefaa3e31ced1f7
RUN git init /src && cd /src \
  && git remote add origin "$OPENSCAD_REPO" \
  && git fetch --depth 1 origin "$OPENSCAD_COMMIT" \
  && git checkout --detach FETCH_HEAD \
  && git submodule update --init --recursive --depth 1

ARG JOBS=2

# HEADLESS: no Qt GUI. EXPERIMENTAL exposes geometry-metrics (enable per run
# with --enable=geometry-metrics). Lib3MF is not packaged for Ubuntu 24.04 and
# only STL/PNG are needed.
RUN cmake -S /src -B /build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DHEADLESS=ON \
      -DEXPERIMENTAL=ON \
      -DENABLE_TESTS=OFF \
      -DUSE_BUILTIN_OPENCSG=ON \
      -DUSE_GLEW=ON \
      -DUSE_CCACHE=OFF \
      -DCMAKE_REQUIRE_FIND_PACKAGE_Lib3MF=OFF \
  && cmake --build /build --parallel ${JOBS} \
  && cmake --install /build \
  && rm -rf /build /src

# PNG export needs a GL context and an X display. xvfb-run hangs for non-root
# users, so start a private Xvfb on an abstract socket instead.
RUN printf '%s\n' \
  '#!/bin/sh' \
  'D=$((100 + $$ % 900))' \
  'Xvfb ":$D" -screen 0 1280x1024x24 -nolisten tcp >/dev/null 2>&1 &' \
  'XVFB_PID=$!' \
  'sleep 0.3' \
  'DISPLAY=":$D" openscad "$@"' \
  'rc=$?' \
  'kill $XVFB_PID 2>/dev/null' \
  'exit $rc' \
  > /usr/local/bin/oscad-run \
  && chmod +x /usr/local/bin/oscad-run

ENV HOME=/tmp
WORKDIR /work
