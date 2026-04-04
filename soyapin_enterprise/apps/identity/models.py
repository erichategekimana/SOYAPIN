from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from infrastructure.models import TimestampMixin

class User(AbstractBaseUser, PermissionsMixin, TimestampMixin):
    class Roles(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        VENDOR = 'vendor', 'Vendor'
        AGENT = 'agent', 'Delivery Agent'
        CUSTOMER = 'customer', 'Customer'
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices)
    phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    
    USERNAME_FIELD = 'email'
    
    objects = UserManager()  # Custom manager

class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    coordinates = PointField(geography=True)  # PostGIS
    is_default = models.BooleanField(default=False)
    
    class Meta:
        indexes = [GistIndex(fields=['coordinates'])]  # Spatial index
