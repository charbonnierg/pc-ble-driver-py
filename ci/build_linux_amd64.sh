#!/usr/bin/env bash

set -eu

apt-get update \
    && python -m pip install cmake \
    && apt-get install -y bison flex ninja-build swig libudev-dev

git clone https://github.com/microsoft/vcpkg /opt/vcpkg \
    && cd /opt/vcpkg \
    && ./bootstrap-vcpkg.sh \
    && cd -

export VCPKG_DEFAULT_TRIPLET="x64-linux"
export VCPKG_ROOT=/opt/vcpkg
export PATH="$VCPKG_ROOT:$PATH"

git clone https://github.com/NordicPlayground/vcpkg-overlay-ports-public.git \
    && vcpkg install --overlay-ports=vcpkg-overlay-ports-public/ports/nrf-ble-driver nrf-ble-driver

export PIP_INDEX_URL="https://pypi.org/simple"

# Create virtual environment if it does not exist yet
if [ ! -d ".venv/" ]; then
  echo -e "Creating virtual environment in $ROOT/.venv directory"
  python3 -m venv .venv
  .venv/bin/python -m pip install -U wheel pip
fi

echo -e "Installing development dependencies"
.venv/bin/python -m pip install -r requirements-dev.txt

echo -e "Building wheel"
.venv/bin/python .py setup.py bdist_wheel --build-type Release
