# main.py
import sys
import os
from pathlib import Path

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

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from rapidocr import RapidOCR
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from typing import Optional

app = FastAPI(title="RapidOCR + Qwen3-0.6B Summarizer (Offline)")

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


class SummaryResponse(BaseModel):
    ocr_text: str
    summary: str
    ocr_lines: Optional[list] = None


def extract_text_from_image(image_bytes: bytes) -> tuple[str, list]:
    result = ocr_engine(image_bytes)
    if result is None or result.txts is None or len(result.txts) == 0:
        return "", []
    lines = list(result.txts)
    return "\n".join(lines), lines


def summarize_with_qwen(text: str, max_new_tokens: int = 256) -> str:
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


@app.post("/ocr-summarize", response_model=SummaryResponse)
async def ocr_and_summarize(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        ocr_text, ocr_lines = extract_text_from_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    if not ocr_text.strip():
        return SummaryResponse(
            ocr_text="",
            summary="No text detected in the image.",
            ocr_lines=[],
        )

    try:
        summary = summarize_with_qwen(ocr_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

    return SummaryResponse(
        ocr_text=ocr_text,
        summary=summary,
        ocr_lines=ocr_lines,
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": str(MODEL_PATH),
        "offline": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)