#!/bin/bash

app=app.py

echo "Current working directory: $current_path"
bash kill_process_by_name.sh $app

# Activate the virtual environment
source venv/bin/activate

# Run the Python script with the appropriate argument
python $app
