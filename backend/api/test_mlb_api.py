# Test script: test_mlb_api.py
import statsapi
import socket

# Set timeout
socket.setdefaulttimeout(30)

print("Testing MLB Stats API connection...")

try:
    # Simple test
    result = statsapi.league_leader_data('homeRuns', season=2025, limit=5)
    print(f"✓ Success! Fetched {len(result)} leaders")
    print(f"Top HR leader: {result[0][1]} with {result[0][2]} home runs")
except Exception as e:
    print(f"✗ Error: {e}")