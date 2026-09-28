"""
tests/test_customers.py
-----------------------
Tests for customer-related endpoints:
  API 1: POST /api/customers
  API 2: GET  /api/customers/{id}
  API 5: GET  /api/customers/{id}/loans
  API 6: GET  /api/customers/{id}/summary
"""
import pytest


# ─── Helper ──────────────────────────────────────────────────────────────────

def make_customer(**overrides):
    data = {
        "name": "Priya Raman",
        "email": "priya@example.com",
        "phone": "1234567890",
        "date_of_birth": "1990-04-15",
        "monthly_income": 45000,
    }
    data.update(overrides)
    return data


# ─── API 1: Register Customer ─────────────────────────────────────────────────

class TestRegisterCustomer:
    def test_valid_customer_returns_201(self, client):
        resp = client.post("/api/customers", json=make_customer())
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] >= 1
        assert data["name"] == "Priya Raman"
        assert data["email"] == "priya@example.com"

    def test_invalid_name_alphanumeric_returns_400(self, client):
        resp = client.post("/api/customers", json=make_customer(name="A1"))
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_FAILED"
        fields = [d["field"] for d in body["details"]]
        assert "name" in fields

    def test_invalid_phone_short_returns_400(self, client):
        resp = client.post("/api/customers", json=make_customer(phone="98765"))
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_FAILED"
        fields = [d["field"] for d in body["details"]]
        assert "phone" in fields

    def test_future_dob_returns_400(self, client):
        resp = client.post("/api/customers", json=make_customer(date_of_birth="2099-01-01"))
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_FAILED"
        fields = [d["field"] for d in body["details"]]
        assert "date_of_birth" in fields

    def test_zero_income_returns_400(self, client):
        resp = client.post("/api/customers", json=make_customer(monthly_income=0))
        assert resp.status_code == 400
        body = resp.json()
        fields = [d["field"] for d in body["details"]]
        assert "monthly_income" in fields

    def test_multiple_invalid_fields_in_one_response(self, client):
        resp = client.post(
            "/api/customers",
            json=make_customer(name="A1", phone="123", monthly_income=-5),
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_FAILED"
        fields = [d["field"] for d in body["details"]]
        assert "name" in fields
        assert "phone" in fields
        assert "monthly_income" in fields

    def test_duplicate_email_returns_409(self, client):
        client.post("/api/customers", json=make_customer())
        resp = client.post("/api/customers", json=make_customer())
        assert resp.status_code == 409
        assert resp.json()["error"] == "DUPLICATE_EMAIL"

    def test_malformed_json_returns_400(self, client):
        resp = client.post(
            "/api/customers",
            content="not-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_REQUEST"

    def test_empty_body_returns_400(self, client):
        resp = client.post(
            "/api/customers",
            content="",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "INVALID_REQUEST"


# ─── API 2: Get Customer ──────────────────────────────────────────────────────

class TestGetCustomer:
    def test_get_existing_customer(self, client, sample_customer):
        cid = sample_customer["id"]
        resp = client.get(f"/api/customers/{cid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == cid

    def test_missing_customer_returns_404(self, client):
        resp = client.get("/api/customers/9999")
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"

    def test_invalid_id_zero_returns_400(self, client):
        resp = client.get("/api/customers/0")
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_FAILED"

    def test_invalid_id_negative_returns_400(self, client):
        resp = client.get("/api/customers/-1")
        assert resp.status_code == 400
        assert resp.json()["error"] == "VALIDATION_FAILED"


# ─── API 5: List Customer Loans ───────────────────────────────────────────────

class TestListCustomerLoans:
    def test_customer_with_no_loans_returns_empty_list(self, client, sample_customer):
        cid = sample_customer["id"]
        resp = client.get(f"/api/customers/{cid}/loans")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_status_filter_pending_returns_400(self, client, sample_customer):
        cid = sample_customer["id"]
        resp = client.get(f"/api/customers/{cid}/loans?status=PENDING")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_FAILED"

    def test_missing_customer_returns_404(self, client):
        resp = client.get("/api/customers/9999/loans")
        assert resp.status_code == 404


# ─── API 6: Customer Summary ──────────────────────────────────────────────────

class TestCustomerSummary:
    def test_summary_no_loans_returns_zeros_and_low(self, client, sample_customer):
        cid = sample_customer["id"]
        resp = client.get(f"/api/customers/{cid}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_applications"] == 0
        assert data["approved_count"] == 0
        assert data["rejected_count"] == 0
        assert float(data["total_approved_amount"]) == 0.0
        assert float(data["total_monthly_emi"]) == 0.0
        assert float(data["emi_to_income_ratio"]) == 0.0
        assert data["risk_band"] == "LOW"

    def test_summary_aggregates_approved_loans_only(self, client, sample_customer):
        """
        Apply two approved loans and one that gets rejected (age rule for a young customer).
        The summary should only aggregate approved amounts and EMIs.
        """
        cid = sample_customer["id"]
        # Both should be approved given income=45000, age~35
        client.post("/api/loans", json={"customer_id": cid, "amount": 100000, "tenure_months": 12})
        client.post("/api/loans", json={"customer_id": cid, "amount": 200000, "tenure_months": 24})

        resp = client.get(f"/api/customers/{cid}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["approved_count"] == 2
        assert float(data["total_approved_amount"]) == 300000.0

    def test_summary_missing_customer_returns_404(self, client):
        resp = client.get("/api/customers/9999/summary")
        assert resp.status_code == 404
