.PHONY: install upgrade test clean build publish publish-test

install:
	uv sync --group dev

upgrade:
	uv sync --upgrade

test:
	uv run pytest

clean:
	rm -rf .venv dist build __pycache__ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:
	uv build

publish: build
	@test -n "$$UV_PUBLISH_TOKEN" || (echo "Set UV_PUBLISH_TOKEN (PyPI API token)" && exit 1)
	uv publish

publish-test: build
	@test -n "$$UV_PUBLISH_TOKEN" || (echo "Set UV_PUBLISH_TOKEN (TestPyPI API token)" && exit 1)
	uv publish --publish-url https://test.pypi.org/legacy/
