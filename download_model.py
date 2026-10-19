from pathlib import Path
from huggingface_hub import snapshot_download

MODEL_ID = "Qwen/Qwen3-0.6B"
LOCAL_DIR = Path("models/Qwen3-0.6B")

print(f"Downloading {MODEL_ID} → {LOCAL_DIR.resolve()}")
snapshot_download(
    repo_id=MODEL_ID,
    local_dir=str(LOCAL_DIR),
    local_dir_use_symlinks=False,   # important for PyInstaller
    ignore_patterns=["*.msgpack", "*.h5", "*.ot"],  # optional cleanup
)
print("Download finished.")

if __name__ == "__main__":
    download()