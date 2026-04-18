import uuid
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from .models import Payment, Order
from .mtn_client import MTNMoMoClient

class PaymentService:
    @staticmethod
    def initiate_mtn_payment(order, phone_number):
        """
        Initiate MTN Mobile Money payment.
        Returns (success, transaction_ref, message)
        """
        try:
            client = MTNMoMoClient()
            # Ensure phone number format: 256XXXXXXXXX (no '+' or spaces)
            phone = phone_number.replace('+', '').replace(' ', '')
            external_id = client.request_to_pay(
                amount=order.total_amount,
                currency="EUR",  # or "UGX", "RWF" – adjust based on your currency
                phone_number=phone,
                external_id=None,
                payer_message=f"Order #{order.id}",
                payee_note="Soyapin purchase"
            )
            # In a real flow, you would poll for status or use a webhook.
            # For simplicity, we'll assume success after a few seconds.
            # We'll check status after 2 seconds (you may implement async).
            import time
            time.sleep(2)
            status = client.get_payment_status(external_id)
            if status.get('status') == 'SUCCESSFUL':
                return True, external_id, "Payment successful"
            else:
                return False, None, f"Payment not successful: {status.get('status')}"
        except Exception as e:
            return False, None, str(e)