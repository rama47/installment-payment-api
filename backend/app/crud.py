from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from . import models, schemas
import uuid

# Installment Order CRUD
def create_installment_order(db: Session, order_data: schemas.InstallmentOrderCreate) -> models.InstallmentOrder:
    # Calculate installment amount if not provided
    if not order_data.installment_amount:
        order_data.installment_amount = order_data.amount / order_data.installment_count
    
    db_order = models.InstallmentOrder(
        customer_id=order_data.customer_id,
        amount=order_data.amount,
        currency=order_data.currency,
        installment_count=order_data.installment_count,
        installment_amount=order_data.installment_amount
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def get_installment_order(db: Session, order_id: str) -> Optional[models.InstallmentOrder]:
    return db.query(models.InstallmentOrder).filter(models.InstallmentOrder.id == order_id).first()

def get_installment_orders(
    db: Session, 
    customer_id: Optional[str] = None, 
    status: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[models.InstallmentOrder]:
    query = db.query(models.InstallmentOrder)
    
    if customer_id:
        query = query.filter(models.InstallmentOrder.customer_id == customer_id)
    if status:
        query = query.filter(models.InstallmentOrder.status == status)
    
    return query.offset(skip).limit(limit).all()

def update_installment_order_status(db: Session, order_id: str, status: str) -> Optional[models.InstallmentOrder]:
    db_order = get_installment_order(db, order_id)
    if db_order:
        db_order.status = status
        db.commit()
        db.refresh(db_order)
    return db_order

# Installment CRUD
def create_installments_for_order(db: Session, order_id: str, installment_amount: float, count: int) -> List[models.Installment]:
    installments = []
    for i in range(1, count + 1):
        # Calculate due date (monthly installments)
        due_date = datetime.utcnow() + timedelta(days=30 * i)
        
        installment = models.Installment(
            order_id=order_id,
            installment_number=i,
            amount=installment_amount,
            due_date=due_date
        )
        installments.append(installment)
    
    db.add_all(installments)
    db.commit()
    
    for installment in installments:
        db.refresh(installment)
    
    return installments

def get_installments_by_order(db: Session, order_id: str) -> List[models.Installment]:
    return db.query(models.Installment).filter(models.Installment.order_id == order_id).all()

def get_due_installments(db: Session) -> List[models.Installment]:
    return db.query(models.Installment).filter(
        and_(
            models.Installment.status == "pending",
            models.Installment.due_date <= datetime.utcnow()
        )
    ).all()

def update_installment_status(db: Session, installment_id: str, status: str) -> Optional[models.Installment]:
    db_installment = db.query(models.Installment).filter(models.Installment.id == installment_id).first()
    if db_installment:
        db_installment.status = status
        db.commit()
        db.refresh(db_installment)
    return db_installment

# Wallet CRUD
def create_wallet(db: Session, wallet_data: schemas.WalletCreate) -> models.Wallet:
    db_wallet = models.Wallet(
        customer_id=wallet_data.customer_id,
        currency=wallet_data.currency
    )
    db.add(db_wallet)
    db.commit()
    db.refresh(db_wallet)
    return db_wallet

def get_wallet(db: Session, customer_id: str) -> Optional[models.Wallet]:
    return db.query(models.Wallet).filter(models.Wallet.customer_id == customer_id).first()

def get_wallet_by_id(db: Session, wallet_id: str) -> Optional[models.Wallet]:
    return db.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()

def update_wallet_balance(db: Session, wallet_id: str, amount: float, transaction_type: str, 
                         description: str = None, reference_id: str = None) -> Optional[models.Wallet]:
    db_wallet = get_wallet_by_id(db, wallet_id)
    if not db_wallet:
        return None
    
    balance_before = db_wallet.balance
    
    if transaction_type == "credit":
        db_wallet.balance += amount
    elif transaction_type == "debit":
        if db_wallet.balance < amount:
            return None  # Insufficient funds
        db_wallet.balance -= amount
    
    # Create ledger entry
    ledger_entry = models.WalletLedger(
        wallet_id=wallet_id,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
        reference_id=reference_id,
        balance_before=balance_before,
        balance_after=db_wallet.balance
    )
    
    db.add(ledger_entry)
    db.commit()
    db.refresh(db_wallet)
    return db_wallet

def get_wallet_ledger(db: Session, wallet_id: str, skip: int = 0, limit: int = 100) -> List[models.WalletLedger]:
    return db.query(models.WalletLedger).filter(
        models.WalletLedger.wallet_id == wallet_id
    ).order_by(desc(models.WalletLedger.created_at)).offset(skip).limit(limit).all()

# Charge CRUD
def create_charge(db: Session, charge_data: schemas.ChargeCreate) -> models.Charge:
    db_charge = models.Charge(
        customer_id=charge_data.customer_id,
        amount=charge_data.amount,
        currency=charge_data.currency,
        installment_id=charge_data.installment_id,
        installment_order_id=charge_data.installment_order_id,
        split_instructions=charge_data.split_instructions
    )
    db.add(db_charge)
    db.commit()
    db.refresh(db_charge)
    return db_charge

def get_charge(db: Session, charge_id: str) -> Optional[models.Charge]:
    return db.query(models.Charge).filter(models.Charge.id == charge_id).first()

def update_charge_status(db: Session, charge_id: str, status: str, 
                        payment_method: str = None, external_charge_id: str = None) -> Optional[models.Charge]:
    db_charge = get_charge(db, charge_id)
    if db_charge:
        db_charge.status = status
        if payment_method:
            db_charge.payment_method = payment_method
        if external_charge_id:
            db_charge.external_charge_id = external_charge_id
        db.commit()
        db.refresh(db_charge)
    return db_charge

def get_charges(
    db: Session, 
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[models.Charge]:
    query = db.query(models.Charge)
    
    if customer_id:
        query = query.filter(models.Charge.customer_id == customer_id)
    if status:
        query = query.filter(models.Charge.status == status)
    
    return query.order_by(desc(models.Charge.created_at)).offset(skip).limit(limit).all()

# Webhook Log CRUD
def create_webhook_log(db: Session, event_type: str, payload: Dict[str, Any]) -> models.WebhookLog:
    db_webhook = models.WebhookLog(
        event_type=event_type,
        payload=payload
    )
    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)
    return db_webhook

def update_webhook_log_status(db: Session, webhook_id: str, status: str, error_message: str = None) -> Optional[models.WebhookLog]:
    db_webhook = db.query(models.WebhookLog).filter(models.WebhookLog.id == webhook_id).first()
    if db_webhook:
        db_webhook.status = status
        if status == "processed":
            db_webhook.processed_at = datetime.utcnow()
        if error_message:
            db_webhook.error_message = error_message
        db.commit()
        db.refresh(db_webhook)
    return db_webhook

def get_webhook_logs(db: Session, skip: int = 0, limit: int = 100) -> List[models.WebhookLog]:
    return db.query(models.WebhookLog).order_by(
        desc(models.WebhookLog.created_at)
    ).offset(skip).limit(limit).all()
