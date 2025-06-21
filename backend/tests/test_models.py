import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, InstallmentOrder, Installment, Wallet, Charge

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_create_installment_order(db):
    order = InstallmentOrder(
        id="order1",
        customer_id="cust1",
        amount=500,
        currency="USD",
        installment_count=5,
        installment_amount=100,
        status="pending"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    assert order.id == "order1"
    assert order.customer_id == "cust1"

def test_create_wallet(db):
    wallet = Wallet(
        id="wallet1",
        customer_id="cust1",
        balance=100.0,
        currency="USD",
        is_active=True
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    assert wallet.customer_id == "cust1"
    assert wallet.balance == 100.0

def test_create_charge(db):
    charge = Charge(
        id="charge1",
        customer_id="cust1",
        amount=50.0,
        currency="USD",
        status="pending"
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    assert charge.amount == 50.0
    assert charge.status == "pending"