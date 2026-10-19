build:
	poetry install 

package: clean
	pyinstaller qwen_app.spec --clean --noconfirm

clean:
	rm -rf build dist
	rm -rf sd_ocr_activity/__pycache__