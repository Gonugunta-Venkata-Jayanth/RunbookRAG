#!/usr/bin/env bash
# Build build/lambda.zip for infra/terraform (python3.12, arm64).
# Usage: scripts/package_lambda.sh && cd infra/terraform && terraform init && terraform apply
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/build/lambda"
ZIP="$ROOT/build/lambda.zip"

rm -rf "$OUT" "$ZIP"
mkdir -p "$OUT"
cp -r "$ROOT/runbookrag" "$ROOT/aws" "$OUT/"
(cd "$ROOT" && python -m runbookrag build --corpus corpus --out "$OUT/index.json")
find "$OUT" -name '__pycache__' -type d -prune -exec rm -rf {} +

# numpy is the only runtime dependency (boto3 ships with the Lambda runtime).
pip install --quiet --target "$OUT" --platform manylinux2014_aarch64 --implementation cp \
  --python-version 3.12 --only-binary=:all: "numpy>=2.0,<3"

(cd "$OUT" && zip -qr9 "$ZIP" .)
echo "Lambda bundle: $ZIP ($(du -h "$ZIP" | cut -f1))"
