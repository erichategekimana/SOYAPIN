from typing import TypeVar, Generic, Type, Optional
from django.db.models import Model, QuerySet

T = TypeVar('T', bound=Model)

class BaseRepository(Generic[T]):
    model: Type[T]
    
    def __init__(self):
        self._model = self.model
    
    def get_by_id(self, pk: int) -> Optional[T]:
        return self._model.objects.filter(pk=pk).first()
    
    def create(self, **data) -> T:
        return self._model.objects.create(**data)
    
    def update(self, instance: T, **data) -> T:
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

# Usage
class ProductRepository(BaseRepository[Product]):
    model = Product
    
    def get_by_vendor(self, vendor_id: int) -> QuerySet[Product]:
        return self._model.objects.filter(vendor_id=vendor_id).select_related('inventory')