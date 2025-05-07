#!/bin/bash
# Installation script for dependencies of account_invoice_import_simple_pdf_ocr
# Copyright 2023 NicolasRamos.es - Nicolás Ramos <hola@nicolasramos.es>

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[+] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_error() {
    echo -e "${RED}[!] $1${NC}"
}

# Header
echo -e "${GREEN}=====================================================${NC}"
echo -e "${GREEN}  Account Invoice Import Simple PDF OCR Dependencies  ${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  print_warning "This script needs to be run as root to install system dependencies."
  print_warning "Please run with sudo or as root."
  exit 1
fi

# Check system type
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    print_error "Cannot detect OS type. This script only supports Debian/Ubuntu."
    exit 1
fi

print_status "Detected OS: $OS $VER"

# Install system dependencies
print_status "Installing system dependencies..."

# Update package lists
apt-get update

# Install common dependencies
apt-get install -y tesseract-ocr poppler-utils

# Install Spanish language for tesseract
apt-get install -y tesseract-ocr-spa

print_status "System dependencies installed successfully."

# Check if Python pip is available
if ! command -v pip3 &> /dev/null; then
    print_warning "pip3 not found. Installing python3-pip..."
    apt-get install -y python3-pip
fi

print_status "Installing Python dependencies..."
pip3 install pdf2image pytesseract regex dateparser pypdf2

# Check Tesseract installation
if ! command -v tesseract &> /dev/null; then
    print_error "Tesseract installation failed."
    exit 1
fi

# Check tessdata directory
TESSDATA_DIR="/usr/share/tesseract-ocr/4.00/tessdata"
if [ ! -d "$TESSDATA_DIR" ]; then
    print_warning "Tesseract data directory not found at expected location: $TESSDATA_DIR"

    # Try to find alternative location
    ALT_TESSDATA_DIR=$(find /usr -name "tessdata" -type d | head -n 1)

    if [ -n "$ALT_TESSDATA_DIR" ]; then
        print_status "Found alternative tessdata directory: $ALT_TESSDATA_DIR"
        print_warning "You may need to update the TESSDATA_PREFIX variable in the Python code."
        echo "Suggested value: TESSDATA_PREFIX = \"$ALT_TESSDATA_DIR\""
    else
        print_error "Could not find tessdata directory. OCR might not work."
    fi
else
    print_status "Tesseract data directory found at: $TESSDATA_DIR"
fi

echo ""
print_status "All dependencies have been installed successfully!"
print_status "To test the OCR functionality, run the module's tests."
echo ""
echo -e "${GREEN}=====================================================${NC}"
