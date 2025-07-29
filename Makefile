.PHONY: install clean

install:
	pip install -r requirements.txt
	playwright install chromium

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
