import os
import sys

# Ensure root project directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import main

if __name__ == "__main__":
    main()
