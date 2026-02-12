import sys
from pathlib import Path

# add backend root to sys.path so top-level modules (settings, etc.) are importable from CLI entrypoints
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# TODO: load via source in bash profile on login instead?
# would drop python-dotenv dependency
from dotenv import load_dotenv

load_dotenv()
