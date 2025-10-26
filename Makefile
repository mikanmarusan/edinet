.PHONY: install install-legacy clean

# Primary installation method using uv
install:
	uv sync
	uv run playwright install chromium

# Legacy installation method for compatibility
install-legacy:
	pip install -r requirements.txt
	playwright install chromium

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
