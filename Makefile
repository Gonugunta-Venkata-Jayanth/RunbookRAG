.PHONY: install lint test test-js eval index demo run docker lambda tf-validate

install:
	pip install -r requirements-dev.txt

lint:
	ruff check .

index:
	python -m runbookrag build

test:
	pytest --cov --cov-report=term-missing

test-js: index
	python scripts/export_parity.py && node --test frontend/tests/engine.test.mjs

eval:
	python scripts/evaluate.py

demo: eval
	python scripts/build_demo.py && python -m http.server -d dist 8080

run: index
	uvicorn api.main:app --reload

docker:
	docker build -t runbookrag . && docker run --rm -p 8000:8000 runbookrag

lambda:
	bash scripts/package_lambda.sh

tf-validate:
	cd infra/terraform && terraform fmt -check && terraform init -backend=false -input=false && terraform validate
