import asyncio
import secrets


def random_string(*args, **kwargs) -> str:
    return secrets.token_urlsafe(*args, **kwargs)


async def run_cmd(
    command: str, check: bool = True, **kwargs
) -> asyncio.subprocess.Process:
    process = await asyncio.create_subprocess_shell(command, **kwargs)
    if check:
        await process.wait()
        if process.returncode != 0:
            raise RuntimeError(
                f"cmd '{command}' failed with return code: {process.returncode}\n" \
                f"stdout: {process.stdout.read().decode('utf-8')}\n" \
                f"stderr: {process.stderr.read().decode('utf-8')}"
            )

    return process
