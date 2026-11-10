import logging
import os
import subprocess
import sys
from pathlib import Path

# Resolve paths relative to the project root.
BASE_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent

# Make the project root available to Python imports.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

EXE_PATH = BASE_DIR / "dist" / "ocr-summarizer" / "ocr-summarizer.exe"
IMAGE_PATH = TESTS_DIR / "001.png"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import after adding BASE_DIR to sys.path.
from app.ocr_event import ActiveEventWindowOCRText


def start_exe(exec_cmd, timeout_sec=15):
    logger.info("Starting module %s", exec_cmd)

    if not isinstance(exec_cmd, list):
        exec_cmd = [str(exec_cmd)]

    startupinfo = None

    if sys.platform in ("win32", "cygwin"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        with subprocess.Popen(
            exec_cmd,
            universal_newlines=True,
            startupinfo=startupinfo,
        ) as proc:
            try:
                proc.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                logger.error(
                    "Task execution timed out (%s seconds). Terminating process.",
                    timeout_sec,
                )
                proc.kill()
                proc.wait()

    except Exception:
        logger.exception("Failed to start the process")


if __name__ == "__main__":
    cor_event = ActiveEventWindowOCRText(
        server_url="",
        user_id="",
        company_id="",
        image_path=str(IMAGE_PATH),
        event_id="",
        timestamp="",
        duration="",
    ).run_ocr_test()


    