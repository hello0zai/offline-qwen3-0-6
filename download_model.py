from pathlib import Path
from huggingface_hub import snapshot_download

def download():
    target_dir = Path(__file__).parent / "model_weights"
    print(f"Downloading Qwen/Qwen3-0.6B into {target_dir}...")
    
    snapshot_download(
        repo_id="Qwen/Qwen3-0.6B",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        ignore_patterns=["*.msgpack", "*.h5", "*.ot", "flax_model*"]
    )
    print("Download completed.")

if __name__ == "__main__":
    download()