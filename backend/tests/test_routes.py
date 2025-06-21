import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_wallet():
    data = {"customer_id": "testuser", "currency": "USD"}
    response = client.post("/wallets", json=data)
    assert response.status_code == 200
    assert response.json()["customer_id"] == "testuser"
    assert response.json()["currency"] == "USD"

def test_create_installment_order():
    data = {
        "customer_id": "testuser2",
        "amount": 1000,
        "currency": "USD",
        "installment_count": 5
    }
    response = client.post("/installments/orders", json=data)
    assert response.status_code == 200
    assert response.json()["customer_id"] == "testuser2"
    assert response.json()["amount"] == 1000
    assert response.json()["installment_count"] == 5