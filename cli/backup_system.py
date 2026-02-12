import argparse
import sys

from site_manager.runner import backup_system as do_backup


def main():
    parser = argparse.ArgumentParser(
        description="Backup system directories (/etc, /root, /srv/certbot)"
    )
    parser.add_argument(
        "--delete-older-than",
        type=int,
        default=7,
        help="Delete backups older than N days (default: 7, negative to disable)",
    )

    args = parser.parse_args()

    try:
        print("Backing up system directories...")
        runner = do_backup(delete_older_than_days=args.delete_older_than)
        print(runner.stdout.read())
        print(runner.stderr.read())
        print("System backup completed")
    except RuntimeError as e:
        print(f"System backup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
