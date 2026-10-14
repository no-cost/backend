import os
import subprocess


def lower_priority() -> None:
    """
    Run the current process, and everything it spawns (ansible, mysqldump, tar, gzip), with the
    lowest CPU priority and the idle I/O class, so maintenance jobs don't slow the sites down.

    The idle I/O class is honored by the mq-deadline (Linux 5.14+) and bfq I/O schedulers.
    """

    os.setpriority(os.PRIO_PROCESS, 0, 19)
    try:
        subprocess.run(
            ["ionice", "-c", "3", "-p", str(os.getpid())],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass  # util-linux not installed, CPU priority is lowered at least
