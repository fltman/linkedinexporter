#!/bin/bash
# Setup script for LinkedIn Post Exporter

echo "LinkedIn Post Exporter - Setup"
echo "==============================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
playwright install chromium

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ".env file created. Edit it to add your credentials (optional)."
fi

echo ""
echo "==============================="
echo "Setup complete!"
echo "==============================="
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Run the exporter: python linkedin_exporter.py"
echo ""
echo "Optional: Edit .env file to add LinkedIn credentials"
echo "  (or just use manual login when prompted)"
echo ""
