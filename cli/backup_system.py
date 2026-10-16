import argparse
import sys

from site_manager.runner import backup_system as do_backup
from utils.priority import lower_priority
from utils.sentry import init_sentry


def main():
    init_sentry("backup_system")
    parser = argparse.ArgumentParser(
        description="Backup system directories (/etc, /root)"
    )
    parser.add_argument(
        "--delete-older-than",
        type=int,
        default=7,
        help="Delete backups older than N days (default: 7, negative to disable)",
    )

    args = parser.parse_args()

    lower_priority()

    try:
        print("Backing up system directories...")
        result = do_backup(delete_older_than_days=args.delete_older_than)
        print(result.stdout)
        print(result.stderr)
        print("System backup completed")
    except RuntimeError as e:
        sys.exit(f"System backup failed: {e}")


if __name__ == "__main__":
    main()
