"""Headroom proxy integration for the benchmark.

Manages the lifecycle of a Headroom proxy process and overrides the
opencode config to route all LLM API calls through Headroom for
context compression.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


def check_headroom() -> tuple[bool, str]:
    """Verify the headroom CLI is installed and usable (proxy-capable).

    Returns (ok, message).
    """
    try:
        result = subprocess.run(
            ["headroom", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return False, f"headroom CLI returned error: {result.stderr.strip()}"
    except FileNotFoundError:
        return False, (
            "headroom CLI not found on PATH. "
            "Install with: pip install 'headroom-ai[all]'"
        )
    except subprocess.TimeoutExpired:
        return False, "headroom CLI timed out"

    # Verify proxy dependencies (httpx) are available
    try:
        import httpx  # noqa: F401
    except ImportError:
        return False, (
            "headroom proxy dependencies missing (httpx not found). "
            "Install with: pip install 'headroom-ai[proxy]' or 'headroom-ai[all]'"
        )

    version = result.stdout.strip() or result.stderr.strip()
    return True, f"headroom available: {version}"


def _find_free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_proxy(port: int, timeout: float = 30.0) -> bool:
    """Wait until the headroom proxy is accepting connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=2)
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


class HeadroomProxy:
    """Manages a headroom proxy process for a benchmark run."""

    def __init__(self, port: int | None = None, upstream_url: str | None = None):
        self.port = port or _find_free_port()
        self.upstream_url = upstream_url
        self.process: subprocess.Popen | None = None

    def start(self) -> None:
        """Start the headroom proxy as a background process."""
        env = os.environ.copy()

        # Tell headroom where the real upstream is
        if self.upstream_url:
            env["OPENAI_TARGET_API_URL"] = self.upstream_url

        # Reasonable defaults for local model benchmarks
        env.setdefault("HEADROOM_REQUEST_TIMEOUT", "600")
        env.setdefault("HEADROOM_CONNECT_TIMEOUT_SECONDS", "30")
        env.setdefault("HEADROOM_DISABLE_KOMPRESS", "1")
        env.setdefault("HEADROOM_NO_CCR", "1")
        env.setdefault("HEADROOM_STATELESS", "1")

        self.process = subprocess.Popen(
            ["headroom", "proxy", "--port", str(self.port)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        if not _wait_for_proxy(self.port):
            self.stop()
            raise RuntimeError(
                f"Headroom proxy failed to start on port {self.port} "
                f"within 30 seconds"
            )

    def stop(self, timeout: float = 10.0) -> None:
        """Stop the headroom proxy."""
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        finally:
            self.process = None

    @property
    def proxy_base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


def override_config_for_headroom(
    config_path: Path,
    proxy_base_url: str,
) -> int:
    """Rewrite provider baseURLs in an opencode config to route through headroom.

    Reads the generated opencode config, overrides the 'baseURL' in every
    provider's options to point at the headroom proxy, and writes it back.
    """
    config = json.loads(config_path.read_text())
    providers = config.get("provider", {})
    modified = 0

    for prov_name, prov_config in providers.items():
        options = prov_config.get("options", {})
        current = options.get("baseURL")
        if current:
            options["baseURL"] = proxy_base_url
            modified += 1

    if modified > 0:
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n"
        )

    return modified
