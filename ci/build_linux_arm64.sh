#!/usr/bin/env bash

set -eu

apt-get update \
    && python3 -m pip install cmake \
    && apt-get install -y bison flex ninja-build swig libudev-dev pkg-config

git clone https://github.com/microsoft/vcpkg /opt/vcpkg \
    && cd /opt/vcpkg \
    && ./bootstrap-vcpkg.sh -useSystemBinaries \
    && cd -

export VCPKG_DEFAULT_TRIPLET="arm64-linux"
export VCPKG_FORCE_SYSTEM_BINARIES=1
export VCPKG_ROOT=/opt/vcpkg
export PATH="$VCPKG_ROOT:$PATH"

git clone https://github.com/NordicPlayground/vcpkg-overlay-ports-public.git \
    && vcpkg install --overlay-ports=vcpkg-overlay-ports-public/ports/nrf-ble-driver nrf-ble-driver

export PIP_INDEX_URL="https://pypi.org/simple"

# Create virtual environment if it does not exist yet
if [ ! -d ".venv/" ]; then
  echo -e "Creating virtual environment in $ROOT/.venv directory"
  python3 -m venv .venv
  .venv/bin/python -m pip install -U wheel pip keyring artifacts-keyring
fi

mkdir -p /opt \
    && git clone https://github.com/scikit-build/scikit-build /opt/scikit-build \
    && .venv/bin/python -m pip install /opt/scikit-build

echo -e "Building wheel"
.venv/bin/python setup.py bdist_wheel --build-type Release
