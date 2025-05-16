#!/bin/bash

# Check if Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 is not installed. Please install it first."
    echo "You can download it from https://www.python.org/downloads/"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment with Python 3.11..."
    python3.11 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOL
API_URL=
API_KEY=
STUDY_NAME=
QUESTIONS_FILE=questions.json
EOL
    echo "Please update the .env file with your configuration."
fi

echo "Setup complete! You can now run the app with:"
echo "streamlit run app.py"