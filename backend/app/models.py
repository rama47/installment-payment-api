from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class InstallmentOrder(Base):
    __tablename__ = "installment_orders"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    installment_count = Column(Integer, nullable=False)
    installment_amount = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, active, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    installments = relationship("Installment", back_populates="order")
    charges = relationship("Charge", back_populates="installment_order")

class Installment(Base):
    __tablename__ = "installments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    order_id = Column(String, ForeignKey("installment_orders.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="pending")  # pending, paid, failed, overdue
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    order = relationship("InstallmentOrder", back_populates="installments")
    charges = relationship("Charge", back_populates="installment")

class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, nullable=False, unique=True)
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    ledger_entries = relationship("WalletLedger", back_populates="wallet")

class WalletLedger(Base):
    __tablename__ = "wallet_ledger"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    wallet_id = Column(String, ForeignKey("wallets.id"), nullable=False)
    transaction_type = Column(String, nullable=False)  # credit, debit
    amount = Column(Float, nullable=False)
    description = Column(Text)
    reference_id = Column(String)  # charge_id or other reference
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    wallet = relationship("Wallet", back_populates="ledger_entries")

class Charge(Base):
    __tablename__ = "charges"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="pending")  # pending, succeeded, failed
    payment_method = Column(String)  # wallet, external
    external_charge_id = Column(String)  # Stripe charge ID
    installment_id = Column(String, ForeignKey("installments.id"))
    installment_order_id = Column(String, ForeignKey("installment_orders.id"))
    split_instructions = Column(JSON)  # Store split instructions
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    installment = relationship("Installment", back_populates="charges")
    installment_order = relationship("InstallmentOrder", back_populates="charges")

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String, nullable=False)  # charge.succeeded, charge.failed
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, processed, failed
    processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
