import os
import subprocess
import time

import httpx
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "http://localhost:80"
UI_URL = "http://localhost:80"


@pytest.fixture(scope="session", autouse=True)
def docker_stack():
    image_tag = os.environ.get("IMAGE_TAG", "local")
    env = {**os.environ, "IMAGE_TAG": image_tag}
    subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            r = httpx.get(f"{API_URL}/health", timeout=2)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        subprocess.run(["docker", "compose", "down"], cwd=REPO_ROOT)
        raise RuntimeError("Stack did not become healthy within 60s")
    yield
    subprocess.run(["docker", "compose", "down"], cwd=REPO_ROOT, check=True)


@pytest.fixture(scope="session")
def api_url():
    return API_URL


@pytest.fixture(scope="session")
def ui_url():
    return UI_URL
