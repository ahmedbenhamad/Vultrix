import subprocess
import logging
import time
import os
import urllib.request
from urllib.error import URLError

logger = logging.getLogger(__name__)

def _wait_for_qdrant_ready(base_url="http://localhost:6333", timeout_seconds=60):
    deadline = time.time() + timeout_seconds
    health_url = f"{base_url}/collections"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except URLError:
            pass
        time.sleep(1)
    return False


def ensure_qdrant_running(container_name="qdrant", force=False):
    """
    Checks if Qdrant Docker container is installed and running.
    If IS_DOCKER is True, skip the check as we assume the container is managed by Compose.
    """
    from .config import IS_DOCKER
    if IS_DOCKER:
        return True
        
    if not force and os.environ.get("QDRANT_CHECKED") == "true":
        return True

    try:
        # 1. Check if docker is installed/accessible
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\033[91m[!] Docker is not installed or not in PATH. Please install Docker to use Qdrant.\033[0m")
        return False

    try:
        # 2. Check if container exists and get its status
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Container exists
            is_running = result.stdout.strip() == "true"
            if not is_running:
                print(f"\033[93m[*] Qdrant container '{container_name}' is stopped. Starting it...\033[0m")
                subprocess.run(["docker", "start", container_name], check=True)
                # Wait for the service to warm up
                if not _wait_for_qdrant_ready():
                    print("\033[91m[!] Qdrant started but did not become ready in time.\033[0m")
                    return False
                print("\033[92m[+] Qdrant started successfully.\033[0m")
            else:
                if not _wait_for_qdrant_ready():
                    print("\033[91m[!] Qdrant is running but not responding yet.\033[0m")
                    return False
            os.environ["QDRANT_CHECKED"] = "true"
            return True
        else:
            # Container does not exist
            print(f"\033[93m[*] Qdrant container '{container_name}' not found. Creating and running it...\033[0m")
            subprocess.run([
                "docker", "run", "-d",
                "-p", "6333:6333",
                "-p", "6334:6334",
                "-v", "qdrant_storage:/qdrant/storage",
                "--name", container_name,
                "qdrant/qdrant"
            ], check=True)
            if not _wait_for_qdrant_ready():
                print("\033[91m[!] Qdrant container started but did not become ready in time.\033[0m")
                return False
            print("\033[92m[+] Qdrant container created and started.\033[0m")
            os.environ["QDRANT_CHECKED"] = "true"
            return True

    except Exception as e:
        print(f"\033[91m[!] Error managing Qdrant Docker: {e}\033[0m")
        return False
