#!/bin/bash
set -e

# Define the plugins directory
PLUGIN_DIR="src/boards/plugins"

echo "Checking for plugin requirements in $PLUGIN_DIR..."

# Check if the directory exists
if [ -d "$PLUGIN_DIR" ]; then
    # Find all requirements.txt files inside immediate subdirectories of plugins
    find "$PLUGIN_DIR" -mindepth 2 -maxdepth 2 -name "requirements.txt" | while read requirements_file; do
        echo "Found requirements: $requirements_file"
        echo "Installing dependencies..."
        # Install to the user directory since we are running as 'appuser'
        pip install --user --no-warn-script-location -r "$requirements_file"
    done
else
    echo "Plugin directory not found at $PLUGIN_DIR"
fi

echo "Starting NHL LED Scoreboard..."

# Execute the main application, passing along any arguments from docker-compose
# We replicate the original ENTRYPOINT here
exec python src/main.py --emulated "$@"