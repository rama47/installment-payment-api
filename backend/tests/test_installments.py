import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.models import InstallmentOrder
from app.schemas import InstallmentOrderCreate

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_create_installment_order():
    response = client.post(
        "/installments/orders",
        json={"customer_id": "test_customer", "amount": 1000, "installment_count": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "test_customer"
    assert data["amount"] == 1000
    assert data["installment_count"] == 10
    assert "id" in data

def test_get_installment_order():
    # First create an order
    response = client.post(
        "/installments/orders",
        json={"customer_id": "test_customer_2", "amount": 2000, "installment_count": 5},
    )
    order_id = response.json()["id"]

    # Now get the order
    response = client.get(f"/installments/orders/{order_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert data["customer_id"] == "test_customer_2"

def test_get_nonexistent_order():
    response = client.get("/installments/orders/nonexistent_id")
    assert response.status_code == 404

def test_get_installments_for_order():
    # First create an order
    response = client.post(
        "/installments/orders",
        json={"customer_id": "test_customer_3", "amount": 1200, "installment_count": 12},
    )
    order_id = response.json()["id"]

    # Now get the installments for the order
    response = client.get(f"/installments/orders/{order_id}/installments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 12
    assert data[0]["order_id"] == order_id
    assert data[0]["installment_number"] == 1
    assert data[0]["amount"] == 100 