"""
Integration tests for backend, from the perspective of the user.
Run this on the deployed server, assuming all services are up and running.
"""

import httpx

BASE_URL = "https://no-cost.site/v1"


async def assert_get_request(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        assert response.status_code == 200
        return response.json()


async def assert_post_request(url: str, data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        assert response.status_code == 200
        return response.json()


async def assert_delete_request(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.delete(url)
        assert response.status_code == 200
        return response.json()


async def main():
    pass


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
