.PHONY: build package clean


build:
	poetry install 

package: clean
	pyinstaller qwen_app.spec --clean --noconfirm
	python tests/test.py

clean:
	rm -rf build dist
