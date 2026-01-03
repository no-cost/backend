"""
Integration tests for backend, from the perspective of the user.
Run this on the deployed server, assuming all services are up and running.
"""

import json
import urllib.request
import urllib.parse

BASE_URL = "https://no-cost.site/v1"


def assert_get_request(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def assert_post_request(url: str, data: dict) -> dict:
    data = urllib.parse.urlencode(data).encode("ascii")
    with urllib.request.urlopen(url, data) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def assert_delete_request(url: str) -> dict:
    with urllib.request.urlopen(
        urllib.request.Request(url, method="DELETE")
    ) as response:
        assert response.status == 200
        return json.loads(response.read().decode("utf-8"))


def main():
    pass


if __name__ == "__main__":
    main()
