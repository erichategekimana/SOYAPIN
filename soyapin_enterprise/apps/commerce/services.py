import uuid
from decimal import Decimal
from django.utils import timezone
from .models import Payment, Order

class MockPaymentGateway:
    """
    Simulates a mobile money or card payment.
    Always succeeds for testing (can be made to fail based on amount).
    """
    @staticmethod
    def process_payment(order: Order, provider: str, phone_number: str = None):
        """
        Mock payment processing.
        Returns (success, transaction_ref, message)
        """
        # Simulate random success (90% success rate for testing)
        import random
        success = random.random() < 0.9
        
        if success:
            transaction_ref = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
            return True, transaction_ref, "Payment successful (mock)"
        else:
            return False, None, "Payment failed (mock)"