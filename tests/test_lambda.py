import io
import json

import pytest

from aws import handlers
from runbookrag.index import save_index


class FakeS3:
    def __init__(self, index):
        self.payload = json.dumps(index).encode()
        self.calls = 0

    def get_object(self, Bucket, Key):
        self.calls += 1
        assert Bucket == "idx-bucket" and Key == "index.json"
        return {"Body": io.BytesIO(self.payload)}


class ConditionalCheckFailedException(Exception):
    pass


class FakeDynamo:
    def __init__(self):
        self.items = {}

    def put_item(self, TableName, Item):
        self.items[Item["query_id"]["S"]] = Item

    def update_item(self, TableName, Key, UpdateExpression, ConditionExpression, ExpressionAttributeValues):
        qid = Key["query_id"]["S"]
        if qid not in self.items:
            raise ConditionalCheckFailedException("ConditionalCheckFailed")
        self.items[qid]["helpful"] = ExpressionAttributeValues[":h"]


@pytest.fixture()
def aws(index, monkeypatch):
    handlers.reset_cache()
    monkeypatch.setenv("RUNBOOKRAG_INDEX_BUCKET", "idx-bucket")
    s3, ddb = FakeS3(index), FakeDynamo()
    yield s3, ddb
    handlers.reset_cache()


def call(aws, method, path, params=None, body=None, b64=False):
    s3, ddb = aws
    raw = json.dumps(body) if body is not None else None
    if b64 and raw:
        import base64

        raw = base64.b64encode(raw.encode()).decode()
    event = {"requestContext": {"http": {"method": method}}, "rawPath": path,
             "queryStringParameters": params, "body": raw, "isBase64Encoded": b64}
    resp = handlers.api_handler(event, None, s3=s3, dynamodb=ddb)
    return resp["statusCode"], json.loads(resp["body"])


def test_health_loads_index_once(aws):
    assert call(aws, "GET", "/health") == (200, {"status": "ok", "chunks": 88})
    call(aws, "GET", "/health")
    assert aws[0].calls == 1


def test_search(aws):
    status, body = call(aws, "GET", "/api/search", {"q": "inode exhaustion", "k": "2"})
    assert status == 200 and len(body["hits"]) == 2 and body["hits"][0]["doc"] == "inode-exhaustion"
    assert call(aws, "GET", "/api/search", {"q": "x"})[0] == 422
    assert call(aws, "GET", "/api/search", {"q": "disk", "k": "abc"})[1]["hits"]


def test_ask_and_feedback(aws):
    status, body = call(aws, "POST", "/api/ask", body={"question": "s3 AccessDenied kms decrypt"}, b64=True)
    assert status == 200 and body["citations"][0].startswith("aws-s3-access-denied#")
    qid = body["query_id"]
    assert aws[1].items[qid]["answered"] == {"BOOL": True}
    assert call(aws, "POST", "/api/feedback", body={"query_id": qid, "helpful": False}) == (200, {"ok": True})
    assert aws[1].items[qid]["helpful"] == {"BOOL": False}
    assert call(aws, "POST", "/api/feedback", body={"query_id": "nope", "helpful": True})[0] == 404
    assert call(aws, "POST", "/api/feedback", body={"query_id": qid})[0] == 422


def test_ask_validation_and_routing(aws):
    assert call(aws, "POST", "/api/ask", body={"question": "x"})[0] == 422
    s3, ddb = aws
    event = {"requestContext": {"http": {"method": "POST"}}, "rawPath": "/api/ask", "body": "not json"}
    assert handlers.api_handler(event, None, s3=s3, dynamodb=ddb)["statusCode"] == 422
    assert call(aws, "OPTIONS", "/api/ask")[0] == 204
    assert call(aws, "GET", "/nope")[0] == 404


def test_feedback_reraises_other_errors(aws):
    class Boom(FakeDynamo):
        def update_item(self, **kwargs):
            raise RuntimeError("throttled")

    event = {"requestContext": {"http": {"method": "POST"}}, "rawPath": "/api/feedback",
             "body": json.dumps({"query_id": "a", "helpful": True})}
    with pytest.raises(RuntimeError):
        handlers.api_handler(event, None, s3=aws[0], dynamodb=Boom())


def test_bundled_index_fallback(index, tmp_path, monkeypatch):
    handlers.reset_cache()
    monkeypatch.delenv("RUNBOOKRAG_INDEX_BUCKET", raising=False)
    monkeypatch.setattr(handlers, "BUNDLED_INDEX", save_index(index, tmp_path / "index.json"))
    assert len(handlers.get_retriever().chunks) == 88
    handlers.reset_cache()
