
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Resolve paths relative to this Python script.
BASE_DIR = Path(__file__).resolve().parents[1]
EXE_PATH = BASE_DIR / "dist" / "ocr-summarizer" / "ocr-summarizer.exe"
BASE_DIR_IMAGE = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR_IMAGE / "001.png"

LOCAL_HOST = "http://127.0.0.1:7601"
HEALTH_URL = f"{LOCAL_HOST}/health"
OCR_URL = f"{LOCAL_HOST}/ocr-summarize"

server_process = None


def start_exe(exe_path: Path) -> subprocess.Popen:
    """Start the OCR summarizer executable."""

    if not exe_path.is_file():
        raise FileNotFoundError(
            f"Executable not found: {exe_path}"
        )

    logger.info("Starting OCR server: %s", exe_path)

    startupinfo = None

    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    process = subprocess.Popen(
        [str(exe_path)],
        cwd=str(exe_path.parent),
        startupinfo=startupinfo,
        stdout=None,
        stderr=None,
    )

    logger.info("OCR server process started. PID: %s", process.pid)
    return process

def check_server_status() -> bool:
    try:
        logger.info("Checking FastAPI server: %s", HEALTH_URL)

        response = requests.get(
            HEALTH_URL,
            timeout=5,
        )

        logger.info("HTTP status: %s", response.status_code)
        logger.info("Response body: %s", response.text)

        response.raise_for_status()

        data = response.json()
        return data.get("status") in ("ok", 200)

    except requests.exceptions.ConnectionError as exc:
        logger.error("Connection failed: %s", exc)

    except requests.exceptions.Timeout:
        logger.error("Request timed out: %s", HEALTH_URL)

    except requests.exceptions.RequestException:
        logger.exception("HTTP request failed")

    except ValueError:
        logger.exception("Invalid JSON response")

    return False


def wait_until_server_is_up(
    process: subprocess.Popen,
    timeout: int = 90,
) -> bool:
    """Wait until the server is ready or the process exits."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if process.poll() is not None:
            logger.error(
                "OCR server exited unexpectedly with code %s",
                process.returncode,
            )
            return False

        if check_server_status():
            logger.info("OCR server is ready.")
            return True

        time.sleep(1)

    logger.error(
        "OCR server did not become ready within %s seconds.",
        timeout,
    )
    return False


def main() -> None:
    """Send an image to the OCR summarization API."""

    if not IMAGE_PATH.is_file():
        logger.error("Image file not found: %s", IMAGE_PATH)
        return

    logger.info("Sending image: %s", IMAGE_PATH)

    try:
        with IMAGE_PATH.open("rb") as image_file:
            response = requests.post(
                OCR_URL,
                files={
                    "file": (
                        IMAGE_PATH.name,
                        image_file,
                        "image/png",
                    )
                },
                timeout=120,
            )

        response.raise_for_status()

        try:
            result = response.json()
            logger.info("OCR result: %s", result)
        except ValueError:
            logger.error(
                "Server returned invalid JSON: %s",
                response.text,
            )

    except requests.exceptions.ConnectionError:
        logger.exception("Cannot connect to OCR API: %s", OCR_URL)

    except requests.exceptions.Timeout:
        logger.exception("OCR request timed out.")

    except requests.exceptions.HTTPError:
        logger.error(
            "HTTP error %s: %s",
            response.status_code,
            response.text,
        )

    except requests.exceptions.RequestException:
        logger.exception("OCR request failed.")


if __name__ == "__main__":
    try:
        server_process = start_exe(EXE_PATH)

        if wait_until_server_is_up(server_process, timeout=60):
            main()
        else:
            logger.error("OCR server startup failed.")

    except (FileNotFoundError, OSError) as exc:
        logger.exception("Could not start OCR server: %s", exc)

    finally:
        # Stop the child process when this launcher exits.
        if server_process is not None and server_process.poll() is None:
            logger.info("Stopping OCR server process.")
            server_process.terminate()

            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()

            logger.info("OCR server stopped.")
