"""Start and health-check the one local vLLM server."""

import argparse
import subprocess
import sys
import time
import urllib.parse
import urllib.request


def _port(base_url: str) -> int:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.port is not None:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def commands(settings) -> list:
    return [
        ["vllm", "serve", settings.local_model, "--port", str(_port(settings.local_base_url)),
         "--max-model-len", "4096",
         "--gpu-memory-utilization", "0.85", "--max-num-seqs", "8",
         "--enable-auto-tool-choice", "--tool-call-parser", "hermes"],
    ]


def _healthy(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=timeout) as response:
            return response.status == 200
    except Exception:  # noqa: BLE001 - a health probe is a boolean
        return False


def _endpoints(settings) -> tuple:
    return tuple(dict.fromkeys((settings.guard_base_url, settings.qa_base_url)))


def check(settings) -> dict:
    health = {url: _healthy(url, settings.model_timeout_s) for url in _endpoints(settings)}
    return {"guard": health[settings.guard_base_url],
            "qa": health[settings.qa_base_url]}


def _wait(settings, timeout_s: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        status = check(settings)
        if all(status.values()):
            return status
        time.sleep(2.0)
    return check(settings)


def start(settings) -> int:
    processes = [subprocess.Popen(command, start_new_session=True) for command in commands(settings)]
    status = _wait(settings)
    if not all(status.values()):
        print(f"Model endpoints are unhealthy: {status}", file=sys.stderr)
        for process in processes:
            process.terminate()
        return 1
    print(f"Model endpoints healthy: {status}")
    return 0


def main(argv=None) -> int:
    from agent.config import load_settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="probe the endpoints and exit")
    args = parser.parse_args(argv)
    settings = load_settings()
    if args.check:
        status = check(settings)
        print(status)
        return 0 if all(status.values()) else 1
    for command in commands(settings):
        print(" ".join(command))
    return start(settings)


if __name__ == "__main__":
    raise SystemExit(main())
