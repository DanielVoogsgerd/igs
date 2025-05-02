#!/bin/bash
# Activate the virtual environment and run the map.py or streamlit app

# Navigate to the directory containing the script
cd "$(dirname "$0")"

# Activate virtual environment
source ./venv/bin/activate

# Check if an argument was passed
if [ "$1" == "streamlit" ]; then
    echo "Starting Streamlit app..."
    streamlit run streamlit_app.py
else
    echo "Running standard map visualization..."
    python map.py
fi

# Deactivate the virtual environment when done (for the map.py case)
if [ "$1" != "streamlit" ]; then
    deactivate
fi