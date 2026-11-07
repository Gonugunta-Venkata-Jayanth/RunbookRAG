"""AWS Lambda handler behind an API Gateway HTTP API (payload format 2.0).

* The index is read from S3 (RUNBOOKRAG_INDEX_BUCKET / RUNBOOKRAG_INDEX_KEY) once per cold
  start, falling back to an index.json bundled with the function.
* Queries and feedback are written to a DynamoDB table (RUNBOOKRAG_TABLE).

boto3 is provided by the Lambda runtime; clients are injectable for tests.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from runbookrag.answer import extractive_answer
from runbookrag.search import MODES, Retriever

BUNDLED_INDEX = Path(__file__).resolve().parent.parent / "index.json"
RETENTION_DAYS = 90
_retriever: Retriever | None = None
_aws_clients: tuple | None = None


def _clients():  # pragma: no cover - exercised only on AWS
    global _aws_clients
    if _aws_clients is None:
        import boto3

        _aws_clients = (boto3.client("s3"), boto3.client("dynamodb"))
    return _aws_clients


def get_retriever(s3=None) -> Retriever:
    global _retriever
    if _retriever is None:
        bucket = os.getenv("RUNBOOKRAG_INDEX_BUCKET")
        if bucket:
            obj = s3.get_object(Bucket=bucket, Key=os.getenv("RUNBOOKRAG_INDEX_KEY", "index.json"))
            index = json.loads(obj["Body"].read())
        else:
            index = json.loads(BUNDLED_INDEX.read_text(encoding="utf-8"))
        _retriever = Retriever(index)
    return _retriever


def reset_cache() -> None:
    global _retriever
    _retriever = None


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json",
                    "Access-Control-Allow-Origin": os.getenv("RUNBOOKRAG_CORS", "*")},
        "body": json.dumps(body),
    }


def _body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def api_handler(event, context, s3=None, dynamodb=None):
    if s3 is None or dynamodb is None:  # pragma: no cover - real AWS clients
        s3, dynamodb = _clients()
    table = os.getenv("RUNBOOKRAG_TABLE", "runbookrag-queries")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")
    params = event.get("queryStringParameters") or {}

    if method == "OPTIONS":
        return _response(204, {})
    if path == "/health":
        return _response(200, {"status": "ok", "chunks": len(get_retriever(s3).chunks)})

    if path == "/api/search" and method == "GET":
        q, mode = (params.get("q") or "").strip(), params.get("mode", "hybrid")
        if len(q) < 2 or mode not in MODES:
            return _response(422, {"error": "q (2+ chars) and a valid mode are required"})
        k = max(1, min(20, int(params.get("k", 5)))) if str(params.get("k", "5")).isdigit() else 5
        hits = get_retriever(s3).search(q, mode=mode, k=k)
        return _response(200, {"query": q, "mode": mode, "hits": [h.to_dict() for h in hits]})

    if path == "/api/ask" and method == "POST":
        data = _body(event)
        question, mode = str(data.get("question", "")).strip(), data.get("mode", "hybrid")
        if not 3 <= len(question) <= 500 or mode not in MODES:
            return _response(422, {"error": "question must be 3-500 chars and mode valid"})
        started = time.perf_counter()
        result = extractive_answer(get_retriever(s3), question, mode=mode)
        latency = round((time.perf_counter() - started) * 1000, 3)
        qid = uuid.uuid4().hex
        dynamodb.put_item(TableName=table, Item={
            "query_id": {"S": qid},
            "ts": {"S": datetime.now(UTC).isoformat()},
            "question": {"S": question},
            "mode": {"S": mode},
            "answered": {"BOOL": result["answer"] is not None},
            "latency_ms": {"N": str(latency)},
            "expires_at": {"N": str(int(time.time()) + RETENTION_DAYS * 86400)},  # DynamoDB TTL
        })
        return _response(200, {**result, "generated": None, "query_id": qid, "latency_ms": latency})

    if path == "/api/feedback" and method == "POST":
        data = _body(event)
        qid, helpful = data.get("query_id"), data.get("helpful")
        if not isinstance(qid, str) or not isinstance(helpful, bool):
            return _response(422, {"error": "query_id (string) and helpful (bool) are required"})
        try:
            dynamodb.update_item(
                TableName=table, Key={"query_id": {"S": qid}},
                UpdateExpression="SET helpful = :h",
                ConditionExpression="attribute_exists(query_id)",
                ExpressionAttributeValues={":h": {"BOOL": helpful}},
            )
        except Exception as exc:
            if "ConditionalCheckFailed" in type(exc).__name__ or "ConditionalCheckFailed" in str(exc):
                return _response(404, {"error": "unknown query_id"})
            raise
        return _response(200, {"ok": True})

    return _response(404, {"error": f"no route for {method} {path}"})
