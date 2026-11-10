.PHONY: build package clean


build:
	poetry install 

package: clean
	python download_model.py
	pyinstaller qwen_app.spec --clean --noconfirm

clean:
	rm -rf build dist
