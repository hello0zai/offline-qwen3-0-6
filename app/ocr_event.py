# main.py
import sys
import os
from pathlib import Path

import json
import platform
import os
import time
import re
import logging
import shutil
import importlib.util
import urllib3
from glob import glob
from pathlib import Path
from datetime import datetime, timezone, timedelta


# ---------- Fix paths for PyInstaller ----------
if getattr(sys, "frozen", False):
    # Running as compiled executable
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

# Force all Hugging Face / Transformers caches inside the bundle
os.environ["HF_HOME"] = str(BASE_DIR / "hf_cache")
os.environ["TRANSFORMERS_CACHE"] = str(BASE_DIR / "hf_cache")
os.environ["HF_HUB_OFFLINE"] = "1"          # force offline mode
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from rapidocr import RapidOCR
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

import cv2
import requests

logger = logging.getLogger(__name__)


# ---------- Local model path ----------
MODEL_PATH = BASE_DIR / "models" / "Qwen3-0.6B"

if not MODEL_PATH.exists():
    raise RuntimeError(f"Model not found at {MODEL_PATH}. Did you run download_models.py?")

print(f"Loading model from: {MODEL_PATH}")

# ---------- Load models once ----------
ocr_engine = RapidOCR()

tokenizer = AutoTokenizer.from_pretrained(
    str(MODEL_PATH),
    local_files_only=True,
)

model = AutoModelForCausalLM.from_pretrained(
    str(MODEL_PATH),
    torch_dtype="auto",
    device_map="auto",
    local_files_only=True,
)
model.eval()

# ---------- Prompt ----------
SUMMARY_PROMPT = """You are a helpful assistant that summarizes OCR-extracted text.

Task: Create a clear, concise summary of the following text extracted from an image.
- Keep the most important information (names, dates, numbers, key facts).
- Remove noise, repeated characters, and OCR artifacts if possible.
- Write the summary in the same language as the original text.
- Maximum 3-5 sentences.

OCR Text:
{ocr_text}

Summary:"""


class ActiveEventWindowOCRText:
    def __init__(self, server_url, user_id, company_id, image_path,
                 event_id, timestamp, duration,
                 warmup=False) -> None:
        super().__init__()
        self._reader_cache = None
        self.server_url = "http://localhost:7600/screenshot/event/screenshots"        
        self.user_id = user_id
        self.company_id = company_id
        self.image_path = image_path
        self.event_id = event_id
        self.timestamp = timestamp
        self.duration = float(duration) if duration != "" else ""
        self.screenshot_id = 0
        self.image_org = ""

    def extract_text_from_image(self, image_bytes: bytes) -> tuple[str, list]:
        result = ocr_engine(image_bytes)
        if result is None or result.txts is None or len(result.txts) == 0:
            return ""
        lines = list(result.txts)
        return "\n".join(lines)


    def summarize_with_qwen(self, text: str, max_new_tokens: int = 256) -> str:
        if not text.strip():
            return ""

        prompt = SUMMARY_PROMPT.format(ocr_text=text)
        messages = [{"role": "user", "content": prompt}]

        text_input = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        model_inputs = tokenizer([text_input], return_tensors="pt").to(model.device)

        with torch.no_grad():
            generated_ids = model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                top_p=0.8,
                top_k=20,
                do_sample=True,
            )

        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
        return tokenizer.decode(output_ids, skip_special_tokens=True).strip()


    def _send_ocr_result(self, summary):
        """Send OCR results to server with error handling."""
        try:
            payload = {
                'screenshot_id': self.screenshot_id,
                'ocr_text': summary
            }
            server_url = "http://localhost:7600/screenshot/update_ocr_text"
            response = requests.post(server_url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as req_e:
            logger.error(f"Error during API request: {req_e}")
        except Exception as e:
            logger.error(f"Error sending OCR result: {e}")

    def run_ocr(self, min_conf=0.9, save_box_info=False, save_conf_info=False):

        img = cv2.imread(self.image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to load image")

        
        ocr_text = None
        try:
            ocr_text= self.extract_text_from_image(img)
        except Exception:
            logger.exception("[OCRText] reader(img) failed during fullscreen_ocr")
            raise


        if not ocr_text.strip():
            summary="No text detected in the image."
            self._send_ocr_result(summary)

        try:
            summary = self.summarize_with_qwen(ocr_text)
        except Exception as e:
            logger.info(f"Summarization failed: {str(e)}")

        self._send_ocr_result(summary)

        filenames = [self.image_org, self.image_path]
        for filename in filenames:                
            try:
                os.remove(filename)
            except OSError as e:
                logger.error("Failed to remove %s : %s", filename, e)

    def run_ocr_test(self, min_conf=0.9, save_box_info=False, save_conf_info=False):
        print("self.image_path", self.image_path)    
        img = cv2.imread(self.image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to load image")

        
        ocr_text = None
        try:
            ocr_text= self.extract_text_from_image(img)
        except Exception:
            logger.exception("[OCRText] reader(img) failed during fullscreen_ocr")
            raise


        if not ocr_text.strip():
            summary="No text detected in the image."
            print(f"summary: {summary}")


        try:
            summary = self.summarize_with_qwen(ocr_text)
        except Exception as e:
            logger.info(f"Summarization failed: {str(e)}")

        print(f"summary: {summary}")

           

        

    