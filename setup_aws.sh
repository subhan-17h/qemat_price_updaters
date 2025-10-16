#!/bin/bash
# AWS EC2 Setup Script for Price Updater
# Run this script on a fresh AWS EC2 instance (Ubuntu/Debian)

set -e  # Exit on error

echo "================================"
echo "Price Updater - AWS EC2 Setup"
echo "================================"

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip
echo "🐍 Installing Python 3 and pip..."
sudo apt-get install -y python3 python3-pip python3-venv git

# Install Firefox ESR (lighter version for servers)
echo "🦊 Installing Firefox..."
sudo apt-get install -y firefox-esr

# Install Gecko Driver (for Selenium)
echo "🔧 Installing GeckoDriver..."
GECKO_VERSION=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
wget https://github.com/mozilla/geckodriver/releases/download/$GECKO_VERSION/geckodriver-$GECKO_VERSION-linux64.tar.gz
tar -xvzf geckodriver-$GECKO_VERSION-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
sudo chmod +x /usr/local/bin/geckodriver
rm geckodriver-$GECKO_VERSION-linux64.tar.gz

# Install Xvfb (virtual display for headless Firefox)
echo "🖥️  Installing Xvfb (virtual display)..."
sudo apt-get install -y xvfb

# Create project directory
echo "📁 Setting up project directory..."
mkdir -p ~/price_updaters
cd ~/price_updaters

echo ""
echo "✅ Base setup complete!"
echo ""
echo "================================"
echo "NEXT STEPS:"
echo "================================"
echo "1. Clone your repository:"
echo "   git clone https://github.com/subhan-17h/qemat_price_updaters.git ."
echo ""
echo "2. Create .env file with your Firebase credentials"
echo ""
echo "3. Upload your test_with_matched.csv file"
echo ""
echo "4. Create virtual environment:"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo ""
echo "5. Install dependencies:"
echo "   pip install -r requirements.txt"
echo ""
echo "6. Run the application:"
echo "   ./run_in_background.sh"
echo "================================"
