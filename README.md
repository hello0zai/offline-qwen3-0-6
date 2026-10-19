
## How to use
```
call conda create -n qwenenv python=3.11.15 -y
conda activate qwenenv
poetry install
pyinstaller --noconfirm --noupx qwen_app.spec
```


