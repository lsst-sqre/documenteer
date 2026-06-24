# Project dev container for documenteer.
# A minimal Python 3.13 base plus uv and the system packages the build needs.
# Kept project-only and COPY-free so a local build and the stoker-derived
# sandbox build are identical.
FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

# The Microsoft base image ships a Yarn apt source whose signing key has
# rotated, so `apt-get update` aborts on it (NO_PUBKEY 62D54FD4003F6525). We
# use npm, not Yarn, so drop the source before updating.
#
# graphviz provides `dot`, used by sphinx-diagrams when building the docs and
# demo technotes (docs/guides/diagrams.rst, demo/rst-technote/diagram.py).
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends graphviz \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# uv is the project's package manager (see uv.lock). Install it system-wide so
# it's on PATH for every user.
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
