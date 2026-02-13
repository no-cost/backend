import asyncio


async def run_cmd_as_tenant(tenant_user: str, command: str, **kwargs):
    return await run_cmd(f"sudo -u {tenant_user} {command}", **kwargs)


async def run_cmd(command: str, check: bool = True, **kwargs):
    process = await asyncio.create_subprocess_shell(command, **kwargs)
    if check:
        await process.wait()
        if process.returncode != 0:
            raise RuntimeError(
                f"cmd '{command}' failed with return code: {process.returncode}\n"
                f"stdout: {process.stdout.read().decode('utf-8')}\n"
                f"stderr: {process.stderr.read().decode('utf-8')}"
            )

    return process
