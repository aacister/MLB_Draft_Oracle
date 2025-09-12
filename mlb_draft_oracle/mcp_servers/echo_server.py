#!/usr/bin/env python3
import sys
import json

def main():
    print("Echo server started", file=sys.stderr)
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            print(f"Received: {line.strip()}", file=sys.stderr)
            # Echo back the input
            print(line.strip())
            sys.stdout.flush()
    except Exception as e:
        print(f"Error in echo server: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

