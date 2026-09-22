"""
One-off smoke test that exercises the FULL FastAPI app (real routing,
real Pydantic validation, real error handlers) against an in-memory fake
Supabase client, so we can verify all the business logic and error
handling works correctly without touching the real database.

Run: python tests_mock_smoke.py
"""

import itertools
import sys


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table):
        self.table = table
        self._filters = []
        self._order = None
        self._mode = "select"
        self._payload = None

    def select(self, *_args, **_kwargs):
        self._mode = "select"
        return self

    def insert(self, payload):
        self._mode = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._mode = "update"
        self._payload = payload
        return self

    def delete(self):
        self._mode = "delete"
        return self

    def eq(self, field, value):
        self._filters.append((field, value))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = self.table.rows

        def matches(row):
            return all(row.get(f) == v for f, v in self._filters)

        if self._mode == "select":
            return FakeResult([r for r in rows if matches(r)])

        if self._mode == "insert":
            new_row = dict(self._payload)
            new_row["id"] = self.table.next_id
            self.table.next_id += 1
            new_row.setdefault("created_at", "2026-01-01T00:00:00Z")
            rows.append(new_row)
            return FakeResult([new_row])

        if self._mode == "update":
            updated = []
            for r in rows:
                if matches(r):
                    r.update(self._payload)
                    updated.append(r)
            return FakeResult(updated)

        if self._mode == "delete":
            to_remove = [r for r in rows if matches(r)]
            for r in to_remove:
                rows.remove(r)
            return FakeResult(to_remove)

        raise RuntimeError("unknown mode")


class FakeTable:
    def __init__(self):
        self.rows = []
        self.next_id = 1

    def query(self):
        return FakeQuery(self)


class FakeStorageBucket:
    def upload(self, *_args, **_kwargs):
        return {"path": "fake"}

    def remove(self, *_args, **_kwargs):
        return {}

    def create_signed_url(self, path, _expires_in):
        return {"signedURL": f"https://fake.supabase.co/{path}?token=fake"}


class FakeStorage:
    def from_(self, _bucket):
        return FakeStorageBucket()


class FakeSupabase:
    def __init__(self):
        self.tables = {}
        self.storage = FakeStorage()

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = FakeTable()
        return self.tables[name].query()


def main():
    import app.supabase_client as sc

    fake = FakeSupabase()
    # Patch the *instance* in place so every module that already did
    # `from app.supabase_client import supabase` sees the fake behavior.
    sc.supabase.table = fake.table
    sc.supabase.storage.from_ = fake.storage.from_

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    failures = []

    def check(label, condition, extra=""):
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {label} {extra}")
        if not condition:
            failures.append(label)

    # ---------------- root ----------------
    r = client.get("/")
    check("GET / returns 200", r.status_code == 200, r.text)

    # ---------------- transactions ----------------
    r = client.post("/transactions/", json={
        "transaction_id": "TXN-TEST-1",
        "order_id": "ORD-1",
        "platform": "Amazon",
        "transaction_type": "purchase",
        "amount": 1200,
        "transaction_date": "2026-09-01",
        "status": "completed",
    })
    check("create transaction -> 201", r.status_code == 201, r.text)
    check("platform_logo auto-filled", r.json().get("platform_logo") == "🛍️", r.text)

    r = client.post("/transactions/", json={
        "transaction_id": "TXN-TEST-1",
        "order_id": "ORD-1",
        "platform": "Amazon",
        "amount": 1200,
        "transaction_date": "2026-09-01",
        "status": "completed",
    })
    check("duplicate transaction_id -> 409", r.status_code == 409, r.text)
    check("duplicate error has readable detail", r.json().get("detail") == "Transaction ID already exists", r.text)

    r = client.post("/transactions/", json={
        "transaction_id": "",
        "order_id": "ORD-2",
        "platform": "Amazon",
        "amount": 100,
        "transaction_date": "2026-09-01",
    })
    check("blank transaction_id -> 422 with string detail", r.status_code == 422 and isinstance(r.json().get("detail"), str), r.text)

    r = client.post("/transactions/", json={
        "transaction_id": "TXN-TEST-2",
        "order_id": "ORD-2",
        "platform": "Flipkart",
        "amount": -5,
        "transaction_date": "2026-09-01",
    })
    check("negative amount -> 422", r.status_code == 422, r.text)

    r = client.get("/transactions/")
    check("list transactions -> 1 row", r.status_code == 200 and len(r.json()) == 1, r.text)

    r = client.get("/transactions/DOES-NOT-EXIST")
    check("get missing transaction -> 404", r.status_code == 404 and r.json()["detail"] == "Transaction not found", r.text)

    r = client.put("/transactions/TXN-TEST-1", json={
        "order_id": "ORD-1-B",
        "platform": "Amazon",
        "amount": 1500,
        "transaction_date": "2026-09-02",
        "status": "pending",
    })
    check("update transaction -> 200", r.status_code == 200 and r.json()["amount"] == 1500, r.text)

    # second transaction for refund flow
    client.post("/transactions/", json={
        "transaction_id": "TXN-TEST-2",
        "order_id": "ORD-2",
        "platform": "Flipkart",
        "amount": 300,
        "transaction_date": "2026-09-05",
        "status": "failed",
    })

    r = client.get("/transactions/")
    check("failed-payment transaction stored", any(t["status"] == "failed" for t in r.json()), r.text)

    # ---------------- refunds ----------------
    r = client.post("/refunds/", json={
        "transaction_id": "DOES-NOT-EXIST",
        "refund_amount": 100,
        "reason": "test",
        "applied_date": "2026-09-01",
        "due_date": "2026-09-05",
    })
    check("refund for missing transaction -> 404", r.status_code == 404, r.text)

    r = client.post("/refunds/", json={
        "transaction_id": "TXN-TEST-1",
        "refund_amount": 1500,
        "reason": "item damaged",
        "applied_date": "2026-09-10",
        "due_date": "2026-09-01",
    })
    check("due_date before applied_date -> 422", r.status_code == 422, r.text)

    r = client.post("/refunds/", json={
        "transaction_id": "TXN-TEST-1",
        "refund_amount": 1500,
        "reason": "item damaged",
        "applied_date": "2026-09-10",
        "due_date": "2099-01-01",
    })
    check("create refund -> 201", r.status_code == 201, r.text)
    body = r.json()
    check("risk_score computed (amount>1000 -> 40)", body["risk_score"] == 40, body)
    check("display_status present", body["display_status"] == "pending", body)
    refund_id = body["id"]

    r = client.post("/refunds/", json={
        "transaction_id": "TXN-TEST-1",
        "refund_amount": 200,
        "reason": "second request",
        "applied_date": "2026-09-11",
        "due_date": "2026-09-20",
    })
    check("2nd refund risk bumped by repeat-refund rule", r.json()["risk_score"] == 20, r.json())

    r = client.get("/refunds/")
    check("list refunds -> 2 rows", r.status_code == 200 and len(r.json()) == 2, r.text)

    r = client.get(f"/refunds/{refund_id}")
    check("get single refund -> 200", r.status_code == 200, r.text)

    r = client.put(f"/refunds/{refund_id}", json={
        "refund_amount": 1500,
        "reason": "item damaged",
        "applied_date": "2020-01-01",
        "due_date": "2020-01-05",  # both in the past, due after applied -> should become overdue
        "status": "pending",
    })
    check("update refund -> overdue display_status", r.json().get("display_status") == "overdue", r.json())

    r = client.get("/refunds/overdue")
    check("overdue endpoint finds both overdue refunds", r.status_code == 200 and len(r.json()) == 2, r.text)

    r = client.get("/refunds/999999")
    check("missing refund -> 404", r.status_code == 404, r.text)

    r = client.delete(f"/refunds/{refund_id}")
    check("delete refund -> 200", r.status_code == 200, r.text)

    # ---------------- evidence ----------------
    r = client.post(
        "/evidence/upload",
        data={"transaction_id": "TXN-TEST-1"},
        files={"file": ("proof.png", b"fakebytes", "image/png")},
    )
    check("evidence upload -> 201", r.status_code == 201, r.text)

    r = client.post(
        "/evidence/upload",
        data={"transaction_id": "TXN-TEST-1"},
        files={"file": ("proof.txt", b"fakebytes", "text/plain")},
    )
    check("bad file type -> 400", r.status_code == 400, r.text)

    r = client.get("/evidence/TXN-TEST-1")
    check("evidence for transaction -> 1 row", r.status_code == 200 and len(r.json()) == 1, r.text)

    r = client.get("/evidence/")
    check("all evidence listing", r.status_code == 200 and len(r.json()) == 1, r.text)

    evidence_id = r.json()[0]["id"]
    r = client.get(f"/evidence/{evidence_id}/link")
    check("evidence signed link -> 200 with url", r.status_code == 200 and r.json().get("url"), r.text)

    # ---------------- dashboard ----------------
    r = client.get("/dashboard/summary")
    check("dashboard summary -> 200", r.status_code == 200, r.text)
    d = r.json()
    check("total_transactions == 2", d["total_transactions"] == 2, d)
    check("failed_payments_count == 1", d["failed_payments_count"] == 1, d)

    r = client.get("/dashboard/risk-summary")
    check("risk-summary -> 200", r.status_code == 200, r.text)

    # ---------------- delete transaction ----------------
    r = client.delete("/transactions/TXN-TEST-1")
    check("delete transaction -> 200", r.status_code == 200, r.text)
    r = client.delete("/transactions/TXN-TEST-1")
    check("delete missing transaction -> 404", r.status_code == 404, r.text)

    print()
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:", failures)
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
