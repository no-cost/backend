import pytest


@pytest.mark.asyncio
async def test_index(client):
    response = await client.get("/v1/")
    assert response.status_code == 200
    assert response.json() == {"message": "hello world"}
