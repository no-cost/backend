import os

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = f"https://api.{os.environ['MAIN_DOMAIN']}"
INTEGRATION_TEST_TOKEN = os.environ.get("INTEGRATION_TEST_TOKEN", "")


@pytest.fixture(scope="module")
def api():
    with httpx.Client(base_url=API_BASE_URL, timeout=60, verify=False) as client:
        yield client
