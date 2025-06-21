from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ...database import get_db
from ... import crud, schemas, models
from ...celery_tasks import schedule_installment_charge

router = APIRouter()

@router.post("/orders", response_model=schemas.InstallmentOrderResponse)
def create_installment_order(
    order_data: schemas.InstallmentOrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new installment order with flexible payment schedule
    """
    # Validate installment amount
    if order_data.installment_amount:
        total_calculated = order_data.installment_amount * order_data.installment_count
        if abs(total_calculated - order_data.amount) > 0.01:  # Allow small rounding differences
            raise HTTPException(
                status_code=400, 
                detail="Installment amount * count must equal total amount"
            )
    
    # Create the installment order
    db_order = crud.create_installment_order(db, order_data)
    
    # Create installments for the order
    installments = crud.create_installments_for_order(
        db, 
        db_order.id, 
        db_order.installment_amount, 
        db_order.installment_count
    )
    
    # Schedule the first installment charge
    if installments:
        background_tasks.add_task(
            schedule_installment_charge,
            installment_id=installments[0].id,
            due_date=installments[0].due_date.isoformat()
        )
    
    return db_order

@router.get("/orders/{order_id}", response_model=schemas.InstallmentOrderResponse)
def get_installment_order(order_id: str, db: Session = Depends(get_db)):
    """
    Get installment order details
    """
    db_order = crud.get_installment_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Installment order not found")
    return db_order

@router.get("/orders", response_model=List[schemas.InstallmentOrderResponse])
def get_installment_orders(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get list of installment orders with optional filtering
    """
    orders = crud.get_installment_orders(db, customer_id, status, skip, limit)
    return orders

@router.get("/orders/{order_id}/installments", response_model=List[schemas.InstallmentResponse])
def get_order_installments(order_id: str, db: Session = Depends(get_db)):
    """
    Get all installments for a specific order
    """
    db_order = crud.get_installment_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Installment order not found")
    
    installments = crud.get_installments_by_order(db, order_id)
    return installments

@router.post("/orders/{order_id}/activate")
def activate_installment_order(order_id: str, db: Session = Depends(get_db)):
    """
    Activate an installment order (change status from pending to active)
    """
    db_order = crud.get_installment_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Installment order not found")
    
    if db_order.status != "pending":
        raise HTTPException(status_code=400, detail="Order is not in pending status")
    
    updated_order = crud.update_installment_order_status(db, order_id, "active")
    return {"message": "Installment order activated successfully", "order": updated_order}

@router.get("/due-installments", response_model=List[schemas.InstallmentResponse])
def get_due_installments(db: Session = Depends(get_db)):
    """
    Get all installments that are due for payment
    """
    installments = crud.get_due_installments(db)
    return installments

@router.post("/installments/{installment_id}/process")
def process_installment_payment(
    installment_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Process payment for a specific installment
    """
    db_installment = crud.get_installments_by_order(db, installment_id)
    if not db_installment:
        raise HTTPException(status_code=404, detail="Installment not found")
    
    # This would typically trigger the charge creation and processing
    # For now, we'll just update the status
    updated_installment = crud.update_installment_status(db, installment_id, "processing")
    
    # Schedule the charge processing
    background_tasks.add_task(
        process_installment_charge,
        installment_id=installment_id
    )
    
    return {"message": "Installment payment processing started", "installment": updated_installment}

def process_installment_charge(installment_id: str):
    """
    Background task to process installment charge
    """
    # This would be implemented in the Celery worker
    # For now, it's a placeholder
    pass
