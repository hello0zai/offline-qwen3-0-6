import sys
import multiprocessing
from pathlib import Path
from contextlib import asynccontextmanager

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

models = {}

def resolve_resource_path(relative_path: str) -> Path:
    """Resolve paths for normal execution and PyInstaller packages."""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent
    return base_path / relative_path

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load Qwen3-0.6B into memory on startup."""
    model_dir = resolve_resource_path("model_weights")
    if not model_dir.exists():
        print(f"Error: Model directory not found at {model_dir}", file=sys.stderr)
        sys.exit(1)

    print("Loading Qwen3-0.6B tokenizer and weights...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    models["device"] = device
    models["tokenizer"] = AutoTokenizer.from_pretrained(
        str(model_dir),
        local_files_only=True,
        trust_remote_code=True
    )
    models["llm"] = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        torch_dtype=dtype,
        device_map=device,
        local_files_only=True,
        trust_remote_code=True
    )
    print(f"Server ready. Running on {device.upper()}.")
    yield
    models.clear()

app = FastAPI(title="Qwen3 Text Summarizer API", lifespan=lifespan)

class TextPayload(BaseModel):
    text: str

@app.post("/api/summarize-text")
async def summarize_text(payload: TextPayload):
    text_content = payload.text.strip()
    if not text_content:
        raise HTTPException(status_code=400, detail="Text field cannot be empty.")

    tokenizer = models["tokenizer"]
    model = models["llm"]
    device = models["device"]

    messages = [
        {
            "role": "system",
            "content": "You are a concise document assistant. Clean up and summarize raw OCR text into clear key points."
        },
        {
            "role": "user",
            "content": f"OCR Text:\n\"\"\"\n{text_content}\n\"\"\"\n\nSummary:"
        }
    ]

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([prompt], return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=350,
            temperature=0.3,
            top_p=0.8,
            do_sample=True
        )

    generated_ids = [
        out[len(inp):] for inp, out in zip(inputs.input_ids, outputs)
    ]
    summary = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

    return {
        "status": "success",
        "summary": summary
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")