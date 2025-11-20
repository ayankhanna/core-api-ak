.PHONY: start install dev test deploy clean help

help:
	@echo "Available commands:"
	@echo "  make start    - Start the API server (auto-activates venv)"
	@echo "  make install  - Install dependencies"
	@echo "  make test     - Run tests"
	@echo "  make deploy   - Deploy to Vercel"
	@echo "  make clean    - Clean up cache files"

start:
	@echo "🚀 Starting Core API..."
	@bash -c "source venv/bin/activate && python dev.py"

install:
	@echo "📦 Installing dependencies..."
	@bash -c "source venv/bin/activate && pip install -r requirements.txt"

dev: start

test:
	@echo "🧪 Running tests..."
	@bash -c "source venv/bin/activate && pytest"

deploy:
	@echo "🚢 Deploying to Vercel..."
	@vercel --prod

clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✨ Clean complete!"

