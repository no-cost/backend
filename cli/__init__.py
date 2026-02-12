import sys
from pathlib import Path

# add backend root to sys.path so top-level modules (settings, etc.) are importable from CLI entrypoints
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ugh unfortunately has to depend on python-dotenv for CLI scripts,
# even despite systemd using EnvironmentFile
# and cron jobs can't use something like .bashrc to load env vars
# so python-dotenv covers all non-shell uses
from dotenv import load_dotenv

load_dotenv()
