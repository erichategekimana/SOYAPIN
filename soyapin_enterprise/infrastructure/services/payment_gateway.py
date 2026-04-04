from abc import ABC, abstractmethod
from typing import Dict

class PaymentStrategy(ABC):
    @abstractmethod
    def process(self, amount: Decimal, phone: str) -> Dict:
        pass

class MTNMobileMoney(PaymentStrategy):
    def process(self, amount, phone):
        # Integration with MTN API
        return {"status": "success", "ref": "MTN123"}

class PaymentContext:
    def __init__(self, strategy: PaymentStrategy):
        self._strategy = strategy
    
    def execute_payment(self, amount, phone):
        return self._strategy.process(amount, phone)