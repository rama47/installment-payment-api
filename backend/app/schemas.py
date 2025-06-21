from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# Installment Order Schemas
class InstallmentOrderCreate(BaseModel):
    customer_id: str = Field(..., description="Customer ID")
    amount: float = Field(..., gt=0, description="Total order amount")
    currency: str = Field(default="USD", description="Currency code")
    installment_count: int = Field(..., gt=0, le=24, description="Number of installments")
    installment_amount: Optional[float] = Field(None, description="Amount per installment")

class InstallmentOrderResponse(BaseModel):
    id: str
    customer_id: str
    amount: float
    currency: str
    installment_count: int
    installment_amount: float
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Installment Schemas
class InstallmentResponse(BaseModel):
    id: str
    order_id: str
    installment_number: int
    amount: float
    due_date: datetime
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Wallet Schemas
class WalletCreate(BaseModel):
    customer_id: str = Field(..., description="Customer ID")
    currency: str = Field(default="USD", description="Currency code")

class WalletResponse(BaseModel):
    id: str
    customer_id: str
    balance: float
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class WalletLedgerResponse(BaseModel):
    id: str
    wallet_id: str
    transaction_type: str
    amount: float
    description: Optional[str]
    reference_id: Optional[str]
    balance_before: float
    balance_after: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# Charge Schemas
class ChargeCreate(BaseModel):
    customer_id: str = Field(..., description="Customer ID")
    amount: float = Field(..., gt=0, description="Charge amount")
    currency: str = Field(default="USD", description="Currency code")
    installment_id: Optional[str] = Field(None, description="Installment ID if charging for installment")
    installment_order_id: Optional[str] = Field(None, description="Installment order ID")
    split_instructions: Optional[Dict[str, Any]] = Field(None, description="Split instructions for the charge")

class ChargeResponse(BaseModel):
    id: str
    customer_id: str
    amount: float
    currency: str
    status: str
    payment_method: Optional[str]
    external_charge_id: Optional[str]
    installment_id: Optional[str]
    installment_order_id: Optional[str]
    split_instructions: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Webhook Schemas
class WebhookEvent(BaseModel):
    event_type: str = Field(..., description="Event type (charge.succeeded, charge.failed)")
    charge_id: str = Field(..., description="Charge ID")
    amount: float = Field(..., description="Charge amount")
    currency: str = Field(default="USD", description="Currency code")
    status: str = Field(..., description="Charge status")
    split_instructions: Optional[Dict[str, Any]] = Field(None, description="Split instructions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class WebhookLogResponse(BaseModel):
    id: str
    event_type: str
    payload: Dict[str, Any]
    status: str
    processed_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# API Response Schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
