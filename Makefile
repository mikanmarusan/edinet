.PHONY: install install-legacy clean

# Primary installation method using uv
install:
	uv sync

# Legacy installation method for compatibility
install-legacy:
	pip install -r requirements.txt

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
