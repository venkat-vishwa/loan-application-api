"""
tests/test_loans.py
-------------------
Tests for loan-related endpoints:
  API 3: POST /api/loans
  API 4: GET  /api/loans/{id}
"""
import pytest
from decimal import Decimal


# ─── Helpers ─────────────────────────────────────────────────────────────────

def register_customer(client, **overrides) -> dict:
    data = {
        "name": "Priya Raman",
        "email": "priya@example.com",
        "phone": "1234567890",
        "date_of_birth": "1990-04-15",   # ~35 years old
        "monthly_income": 45000,
    }
    data.update(overrides)
    resp = client.post("/api/customers", json=data)
    assert resp.status_code == 201, resp.text
    return resp.json()


def apply_loan(client, customer_id: int, amount=300000, tenure=36) -> dict:
    resp = client.post(
        "/api/loans",
        json={"customer_id": customer_id, "amount": amount, "tenure_months": tenure},
    )
    return resp


# ─── API 3: Apply for a Loan ─────────────────────────────────────────────────

class TestApplyLoan:
    def test_valid_loan_approved_returns_201(self, client):
        c = register_customer(client)
        resp = apply_loan(client, c["id"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "APPROVED"
        assert data["rejection_reason"] is None
        # Verify EMI ~ 9964.29 for 300000 at 12% for 36 months
        assert abs(float(data["emi"]) - 9964.29) < 0.02

    def test_valid_loan_emi_calculation(self, client):
        """300,000 at 12% p.a. for 36 months → EMI = 9,964.29"""
        c = register_customer(client)
        resp = apply_loan(client, c["id"], amount=300000, tenure=36)
        assert resp.status_code == 201
        assert round(float(resp.json()["emi"]), 2) == 9964.29

    def test_amount_too_small_returns_400(self, client):
        c = register_customer(client)
        resp = apply_loan(client, c["id"], amount=500)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_FAILED"
        assert any(d["field"] == "amount" for d in body["details"])

    def test_invalid_tenure_returns_400(self, client):
        c = register_customer(client)
        resp = apply_loan(client, c["id"], tenure=18)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "VALIDATION_FAILED"
        assert any(d["field"] == "tenure_months" for d in body["details"])

    def test_missing_customer_returns_404(self, client):
        resp = apply_loan(client, customer_id=9999)
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"

    # ── Eligibility Rule: Age ─────────────────────────────────────────────────

    def test_young_customer_age_19_rejected(self, client):
        """Customer aged 19 should be REJECTED with the age reason."""
        from datetime import date, timedelta
        young_dob = str(date.today().replace(year=date.today().year - 19))
        # Use a unique email for this customer
        c = register_customer(
            client,
            email="young@example.com",
            date_of_birth=young_dob,
        )
        resp = apply_loan(client, c["id"])
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert "age" in data["rejection_reason"]
        # Application is saved even when rejected
        assert data["id"] >= 1

    # ── Eligibility Rule: Income ──────────────────────────────────────────────

    def test_amount_exceeds_20x_income_rejected(self, client):
        """1,000,000 amount with income 40,000 → exceeds 20×40,000=800,000."""
        c = register_customer(
            client,
            email="income@example.com",
            monthly_income=40000,
        )
        resp = apply_loan(client, c["id"], amount=1000000)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert "income" in data["rejection_reason"]

    # ── Eligibility Rule: Active Loans ────────────────────────────────────────

    def test_third_loan_rejected_by_active_loan_rule(self, client):
        """Customer with 2 approved loans should have 3rd rejected."""
        c = register_customer(client, monthly_income=100000)
        # Loan 1 & 2 should be approved
        r1 = apply_loan(client, c["id"], amount=100000, tenure=12)
        r2 = apply_loan(client, c["id"], amount=100000, tenure=24)
        assert r1.json()["status"] == "APPROVED"
        assert r2.json()["status"] == "APPROVED"

        # Loan 3 should be rejected
        r3 = apply_loan(client, c["id"], amount=100000, tenure=36)
        assert r3.status_code == 201
        data = r3.json()
        assert data["status"] == "REJECTED"
        assert "2 active loans" in data["rejection_reason"]

    # ── Rejected loan has null EMI ────────────────────────────────────────────

    def test_rejected_loan_emi_is_null(self, client):
        from datetime import date
        young_dob = str(date.today().replace(year=date.today().year - 19))
        c = register_customer(client, email="nullemi@example.com", date_of_birth=young_dob)
        resp = apply_loan(client, c["id"])
        assert resp.json()["emi"] is None

    # ── Interest rate assignment ──────────────────────────────────────────────

    @pytest.mark.parametrize("tenure, expected_rate", [
        (12, 10.0),
        (24, 11.0),
        (36, 12.0),
        (48, 13.0),
        (60, 13.0),
    ])
    def test_interest_rate_by_tenure(self, client, tenure, expected_rate):
        c = register_customer(client, email=f"rate{tenure}@example.com", monthly_income=200000)
        resp = apply_loan(client, c["id"], amount=100000, tenure=tenure)
        assert resp.status_code == 201
        assert float(resp.json()["interest_rate"]) == expected_rate


# ─── API 4: Get Loan ──────────────────────────────────────────────────────────

class TestGetLoan:
    def test_get_existing_loan(self, client):
        c = register_customer(client)
        loan = apply_loan(client, c["id"]).json()
        resp = client.get(f"/api/loans/{loan['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == loan["id"]

    def test_missing_loan_returns_404(self, client):
        resp = client.get("/api/loans/9999")
        assert resp.status_code == 404
        assert resp.json()["error"] == "NOT_FOUND"

    def test_zero_id_returns_400(self, client):
        resp = client.get("/api/loans/0")
        assert resp.status_code == 400

    def test_negative_id_returns_400(self, client):
        resp = client.get("/api/loans/-5")
        assert resp.status_code == 400
