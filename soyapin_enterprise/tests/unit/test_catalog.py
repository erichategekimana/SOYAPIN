import pytest
from factories import ProductFactory, VendorFactory

@pytest.mark.django_db
class TestInventoryReservation:
    def test_stock_reservation(self):
        product = ProductFactory(inventory__quantity=10)
        product.inventory.reserve_stock(5)
        
        assert product.inventory.quantity == 5
    
    def test_insufficient_stock_raises_exception(self):
        product = ProductFactory(inventory__quantity=2)
        
        with pytest.raises(InsufficientStockException):
            product.inventory.reserve_stock(5)