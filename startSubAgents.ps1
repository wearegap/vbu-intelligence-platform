# Start Gong Agent
Start-Process cmd.exe -ArgumentList "/k python gongClient.py serve 8765"

# Start Anthropic Agent
Start-Process cmd.exe -ArgumentList "/k python anthropicClient.py serve 8766"
