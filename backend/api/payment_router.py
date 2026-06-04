try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    razorpay = None
    RAZORPAY_AVAILABLE = False

import os
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.security.dependencies import require_role

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[Depends(require_role("recruiter", "hr"))]
)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_default_key")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "default_secret")

if RAZORPAY_AVAILABLE:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    client = None
    print("--> WARNING: razorpay module not found. Payment features will be disabled.")

@router.get("/key-id")
async def get_key_id():
    """Return the Razorpay Key ID to the frontend for initialization."""
    return {"key_id": RAZORPAY_KEY_ID}

class PaymentOrder(BaseModel):
    amount: float
    currency: str = "INR"
    receipt: Optional[str] = None

@router.post("/create-order")
async def create_order(order: PaymentOrder):

    if not client:
        amount_smallest_unit = int(float(order.amount) * 100)
        fake_order_id = f"order_demo_{uuid.uuid4().hex[:12]}"
        return {
            "id": fake_order_id,
            "amount": amount_smallest_unit,
            "currency": order.currency,
            "status": "created",
        }

    try:

        order_data = {
            "amount": int(float(order.amount) * 100),
            "currency": order.currency,
            "receipt": order.receipt,
            "payment_capture": 1,                
        }
        razorpay_order = client.order.create(data=order_data)
        return razorpay_order
    except Exception as e:
        error_msg = str(e)
        print(f"Razorpay Order Error: {error_msg}")
        if "Authentication failed" in error_msg:
            error_msg = "Invalid Razorpay credentials. Please check RAZORPAY_KEY_ID and SECRET in .env"
        raise HTTPException(status_code=400, detail=error_msg)

class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.post("/verify-payment")
async def verify_payment(verification: PaymentVerification):

    if not client:
        return {"status": "success", "message": "Payment verification skipped (demo mode)"}

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": verification.razorpay_order_id,
                "razorpay_payment_id": verification.razorpay_payment_id,
                "razorpay_signature": verification.razorpay_signature,
            }
        )
        return {"status": "success", "message": "Payment verified successfully"}
    except Exception:
        raise HTTPException(status_code=400, detail="Payment verification failed")