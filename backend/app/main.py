from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

from .database import engine, get_db
from . import models, schemas, crud
from .api.endpoints import installments

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Payments API",
    description="A comprehensive payments API with installment orders, wallet management, and webhook handling",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(installments.router, prefix="/installments", tags=["installments"])

# Wallet endpoints
@app.get("/wallets", response_model=List[schemas.WalletResponse])
def get_wallets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get a list of all wallets.
    """
    wallets = db.query(models.Wallet).offset(skip).limit(limit).all()
    return wallets
@app.post("/wallets", response_model=schemas.WalletResponse)
def create_wallet(wallet_data: schemas.WalletCreate, db: Session = Depends(get_db)):
    """
    Create a new wallet for a customer
    """
    # Check if wallet already exists
    existing_wallet = crud.get_wallet(db, wallet_data.customer_id)
    if existing_wallet:
        raise HTTPException(status_code=400, detail="Wallet already exists for this customer")
    
    return crud.create_wallet(db, wallet_data)

@app.get("/wallets/{customer_id}", response_model=schemas.WalletResponse)
def get_wallet(customer_id: str, db: Session = Depends(get_db)):
    """
    Get wallet details for a customer
    """
    wallet = crud.get_wallet(db, customer_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet

@app.get("/wallets/{customer_id}/ledger", response_model=List[schemas.WalletLedgerResponse])
def get_wallet_ledger(
    customer_id: str, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Get wallet transaction ledger
    """
    wallet = crud.get_wallet(db, customer_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    ledger = crud.get_wallet_ledger(db, str(wallet.id), skip, limit)
    return ledger

@app.post("/wallets/{customer_id}/credit")
def credit_wallet(
    customer_id: str, 
    amount: float, 
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Credit a wallet with funds
    """
    wallet = crud.get_wallet(db, customer_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    updated_wallet = crud.update_wallet_balance(
        db, 
        str(wallet.id), 
        amount, 
        "credit",
        description or "Wallet credit"
    )
    
    if not updated_wallet:
        raise HTTPException(status_code=500, detail="Failed to update wallet")
    
    return {"message": "Wallet credited successfully", "new_balance": updated_wallet.balance}

# Charge endpoints
@app.post("/charges", response_model=schemas.ChargeResponse)
def create_charge(charge_data: schemas.ChargeCreate, db: Session = Depends(get_db)):
    """
    Create a new charge (wallet first, then external payment)
    """
    return crud.create_charge(db, charge_data)

@app.get("/charges/{charge_id}", response_model=schemas.ChargeResponse)
def get_charge(charge_id: str, db: Session = Depends(get_db)):
    """
    Get charge details
    """
    charge = crud.get_charge(db, charge_id)
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found")
    return charge

@app.get("/charges", response_model=List[schemas.ChargeResponse])
def get_charges(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get list of charges with optional filtering
    """
    charges = crud.get_charges(db, customer_id, status, skip, limit)
    return charges

# Webhook endpoints
@app.get("/webhooks", response_model=List[schemas.WebhookLogResponse])
def get_webhook_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get webhook logs
    """
    logs = crud.get_webhook_logs(db, skip, limit)
    return logs

@app.get("/webhooks/{webhook_id}", response_model=schemas.WebhookLogResponse)
def get_webhook_log(webhook_id: str, db: Session = Depends(get_db)):
    """
    Get specific webhook log
    """
    log = db.query(models.WebhookLog).filter(models.WebhookLog.id == webhook_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Webhook log not found")
    return log

# Health check
@app.get("/health")
def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "payments-api"}

# Root endpoint
@app.get("/")
def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "Payments API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "installments": "/installments",
            "wallets": "/wallets",
            "charges": "/charges",
            "webhooks": "/webhooks"
        }
    }
