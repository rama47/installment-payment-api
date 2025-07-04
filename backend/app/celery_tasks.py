# This file contains Celery task imports and definitions
# The actual tasks are defined in celery_worker.py

from celery import Celery

celery = Celery("ins_py_api")
# celery.conf.update(...)

from celery_worker import schedule_installment_charge, process_charge, send_webhook_event

__all__ = [
    "celery",
    "schedule_installment_charge",
    "process_charge", 
    "send_webhook_event"
] 