.PHONY: test smoke lint install-dev

install-dev:
	pip install -r skills/easybib/scripts/requirements.txt
	pip install -r skills/easybib/scripts/requirements-dev.txt

test:
	pytest -q

smoke:
	EASYBIB_LIVE=1 pytest -q tests/smoke

lint:
	ruff check .
