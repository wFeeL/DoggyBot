import time
from yookassa import Configuration, Receipt
from yookassa import Payment
from yookassa.domain.models.currency import Currency
from yookassa.domain.models.receipt import Receipt
from yookassa.domain.common.confirmation_type import ConfirmationType
from yookassa.domain.request.payment_request_builder import PaymentRequestBuilder
import yookassa.invoice

from env import shop_id, secret_key

Configuration.configure(str(shop_id), secret_key)

def create_invoice(price: int, length: int):
    receipt = Receipt()
    receipt.customer = {"phone": "79123456789", "email": "receipt@receipt.com"}
    receipt.tax_system_code = 1
    receipt.items = [
        {
            "description": f"Подписка на {length} дня",
            "quantity": 2.0,
            "amount": {
                "value": float(price),
                "currency": Currency.RUB
            },
            "vat_code": 2
        }
    ]
    builder = PaymentRequestBuilder()
    builder.set_amount({"value": float(price), "currency": Currency.RUB}) \
        .set_confirmation({"type": ConfirmationType.REDIRECT, "return_url": "https://t.me/doggylogy_dev_bot"}) \
        .set_capture(True) \
        .set_description("Подписка на 93 дня") \
        .set_receipt(receipt)
        
    request = builder.build()
    invoice = Payment.create(request)
    return invoice.confirmation.confirmation_url, invoice.id

def check_invoice(invoice_id: str, summ: int):
    paym = Payment.find_one(invoice_id)
    
    if paym.status == "waiting_for_capture":
        Payment.capture(invoice_id, {
            "amount": {
                "value": str(float(summ)),
                "currency": "RUB"
            }
        })
        return 1
    
    elif paym.status == "succeeded":
        return 1
    
    elif paym.status == "pending":
        return 0
    
    elif paym.status == "canceled":
        return -1
