from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv
import stripe
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import crud, models, schemas

load_dotenv()

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "payments_api",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.celery_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

@celery_app.task
def schedule_installment_charge(installment_id: str, due_date: str):
    """
    Schedule a charge for an installment
    """
    db = get_db()
    try:
        # Get the installment
        installments = crud.get_installments_by_order(db, installment_id)
        if not installments:
            return {"error": "Installment not found"}
        
        installment = installments[0]
        
        # Create a charge for this installment
        charge_data = schemas.ChargeCreate(
            customer_id=installment.order.customer_id,
            amount=installment.amount,
            currency=installment.order.currency,
            installment_id=installment.id,
            installment_order_id=installment.order_id
        )
        
        charge = crud.create_charge(db, charge_data)
        
        # Process the charge
        process_charge.delay(charge.id)
        
        return {"success": True, "charge_id": charge.id}
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def process_charge(charge_id: str):
    """
    Process a charge using wallet first, then external payment
    """
    db = get_db()
    try:
        charge = crud.get_charge(db, charge_id)
        if not charge:
            return {"error": "Charge not found"}

        customer_id = str(charge.customer_id)
        charge_amount = float(charge.amount)
        charge_currency = str(charge.currency)
        charge_installment_id = str(charge.installment_id) if charge.installment_id is not None else None
        charge_installment_order_id = str(charge.installment_order_id) if charge.installment_order_id is not None else None

        wallet = crud.get_wallet(db, customer_id)
        remaining_amount = charge_amount

        if wallet and wallet.balance > 0:
            wallet_id = str(wallet.id)
            wallet_balance = float(wallet.balance)

            if wallet_balance >= charge_amount:
                # Wallet has enough balance to cover the entire charge
                crud.update_wallet_balance(
                    db, wallet_id, charge_amount, "debit",
                    f"Payment for charge {charge_id}", charge_id
                )
                crud.update_charge_status(db, charge_id, "succeeded", "wallet")
                send_webhook_event.delay("charge.succeeded", charge_id)
                return {"success": True, "payment_method": "wallet"}
            else:
                # Wallet has partial balance
                remaining_amount = charge_amount - wallet_balance
                crud.update_wallet_balance(
                    db, wallet_id, wallet_balance, "debit",
                    f"Partial payment for charge {charge_id}", charge_id
                )
        
        # Fallback to external payment (Stripe) for the remaining amount
        try:
            stripe_charge = stripe.Charge.create(
                amount=int(remaining_amount * 100),
                currency=charge_currency.lower(),
                customer=customer_id,
                description=f"Installment payment - Charge {charge_id}",
                metadata={
                    "charge_id": charge_id,
                    "installment_id": charge_installment_id,
                    "installment_order_id": charge_installment_order_id
                }
            )
            crud.update_charge_status(
                db, charge_id, "succeeded", "external", stripe_charge.id
            )
            send_webhook_event.delay("charge.succeeded", charge_id)
            return {"success": True, "payment_method": "external", "stripe_charge_id": stripe_charge.id}

        except stripe.error.StripeError as e:
            # If external payment fails, refund the wallet if it was used
            if wallet and float(wallet.balance) < charge_amount:
                wallet_id = str(wallet.id)
                wallet_balance = float(wallet.balance)
                crud.update_wallet_balance(
                    db, wallet_id, wallet_balance, "credit",
                    f"Refund for failed charge {charge_id}", charge_id
                )
            crud.update_charge_status(db, charge_id, "failed", "external")
            send_webhook_event.delay("charge.failed", charge_id)
            return {"error": str(e), "payment_method": "external"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def send_webhook_event(event_type: str, charge_id: str):
    """
    Send webhook event to configured webhook URLs
    """
    db = get_db()
    try:
        charge = crud.get_charge(db, charge_id)
        if not charge:
            return {"error": "Charge not found"}
        
        # Create webhook payload
        webhook_payload = {
            "event_type": event_type,
            "charge_id": charge.id,
            "customer_id": charge.customer_id,
            "amount": charge.amount,
            "currency": charge.currency,
            "status": charge.status,
            "payment_method": charge.payment_method,
            "external_charge_id": charge.external_charge_id,
            "split_instructions": charge.split_instructions,
            "created_at": charge.created_at.isoformat(),
            "metadata": {
                "installment_id": charge.installment_id,
                "installment_order_id": charge.installment_order_id
            }
        }
        
        # Log webhook event
        webhook_log = crud.create_webhook_log(db, event_type, webhook_payload)
        
        # Send to webhook URLs (configured in environment)
        webhook_urls = os.getenv("WEBHOOK_URLS", "").split(",")
        
        for url in webhook_urls:
            if url.strip():
                try:
                    with httpx.Client(timeout=30.0) as client:
                        response = client.post(
                            url.strip(),
                            json=webhook_payload,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if response.status_code == 200:
                            crud.update_webhook_log_status(db, webhook_log.id, "processed")
                        else:
                            crud.update_webhook_log_status(
                                db, 
                                webhook_log.id, 
                                "failed", 
                                f"HTTP {response.status_code}: {response.text}"
                            )
                
                except Exception as e:
                    crud.update_webhook_log_status(
                        db, 
                        webhook_log.id, 
                        "failed", 
                        str(e)
                    )
        
        return {"success": True, "webhook_log_id": webhook_log.id}
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def process_due_installments():
    """
    Process all due installments (scheduled task)
    """
    db = get_db()
    try:
        due_installments = crud.get_due_installments(db)
        
        for installment in due_installments:
            # Create charge for due installment
            charge_data = schemas.ChargeCreate(
                customer_id=installment.order.customer_id,
                amount=installment.amount,
                currency=installment.order.currency,
                installment_id=installment.id,
                installment_order_id=installment.order_id
            )
            
            charge = crud.create_charge(db, charge_data)
            process_charge.delay(charge.id)
        
        return {"success": True, "processed_count": len(due_installments)}
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

# Schedule periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Process due installments daily at 9 AM UTC
    sender.add_periodic_task(
        crontab(hour=9, minute=0),
        process_due_installments.s(),
        name="process-due-installments-daily"
    )

if __name__ == "__main__":
    celery_app.start()
