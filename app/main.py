import sys
import os
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def resolve_resource_path(relative_path: str) -> Path:
    """Resolve paths for both standard execution and PyInstaller bundles."""
    if hasattr(sys, "_MEIPASS"):
        # Running in a PyInstaller single-file bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in normal development or directory mode
        base_path = Path(__file__).resolve().parent.parent
    return base_path / relative_path

def main():
    model_dir = resolve_resource_path("model_weights")
    if not model_dir.exists():
        print(f"Error: Model directory not found at {model_dir}", file=sys.stderr)
        sys.exit(1)

    print("Loading tokenizer and weights into memory...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir),
        local_files_only=True,
        trust_remote_code=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        torch_dtype=dtype,
        device_map=device,
        local_files_only=True,
        trust_remote_code=True
    )

    print(f"Qwen3-0.6B initialized successfully on {device.upper()}. Type 'exit' to quit.\n")

    history = [
        {"role": "system", "content": "You are a concise, helpful desktop assistant."}
    ]

    while True:
        try:
            user_input = input("User: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break

            history.append({"role": "user", "content": user_input})
            text = tokenizer.apply_chat_template(
                history,
                tokenize=False,
                add_generation_prompt=True
            )
            inputs = tokenizer([text], return_tensors="pt").to(device)

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    top_p=0.8,
                    do_sample=True
                )

            generated_ids = [
                out_ids[len(in_ids):] 
                for in_ids, out_ids in zip(inputs.input_ids, outputs)
            ]
            response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            print(f"\nAssistant: {response.strip()}\n")
            history.append({"role": "assistant", "content": response.strip()})

        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()