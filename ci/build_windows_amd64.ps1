$ErrorActionPreference = "Stop"

# First make sure chocolatey won't prompt for confirmation on install
choco feature enable -n=allowGlobalConfirmation

# Install swig
choco install swig
# Install vs build tools 2017
choco install visualstudio2017buildtools --locale en-US --includeRecommended

# Create a directory where build dependencies will be installed
mkdir build_deps
cd build_deps
# Store the directory path as variable
$BUILD_DEPS_ROOT = "$(pwd)"
# Clone vcpkg
git clone "https://github.com/microsoft/vcpkg"
# Install vcpkg
cd vcpkg
./bootstrap-vcpkg.bat
# Configure vcpkg and add it to the path
$Env:VCPKG_DEFAULT_TRIPLET = "x64-windows"
$Env:VCPKG_ROOT = "$BUILD_DEPS_ROOT" + "\vcpkg"
$Env:PATH += ";$Env:VCPKG_ROOT"

cd ..
git clone "https://github.com/NordicPlayground/vcpkg-overlay-ports-public.git"
vcpkg install --overlay-ports="./vcpkg-overlay-ports-public/ports/nrf-ble-driver" nrf-ble-driver
$Env:CMAKE_PREFIX_PATH = $Env:VCPKG_ROOT + "\packages\nrf-ble-driver_x64-windows\share\nrf-ble-driver"

cd ..
$VenvPath = '.\.venv\Scripts'

if (Test-Path -Path $VenvPath) {
    echo "Installing development dependencies"
    .\.venv\Scripts\python -m pip install -r requirements-dev.txt
} else {
    echo "Creating virtual environment"
    python -m venv .venv
    echo "Installing development dependencies"
    .\.venv\Scripts\python -m pip install -U wheel pip
    .\.venv\Scripts\python -m pip install -r requirements-dev.txt
}

.\.venv\Scripts\python setup.py bdist_wheel --build-type Release
