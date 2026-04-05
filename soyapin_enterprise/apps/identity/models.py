from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.gis.db.models import PointField
from django.db import models
from infrastructure.models.abstract_models import TimestampMixin
from .managers import UserManager  # We'll create this next

class Role(models.Model):
    """
    Matches your SQL: CREATE TABLE roles (id SERIAL PRIMARY KEY, name VARCHAR(50) UNIQUE NOT NULL)
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'roles'
    
    def __str__(self):
        return self.name

class User(AbstractBaseUser, PermissionsMixin, TimestampMixin):
    """
    Matches your SQL users table but uses Django's auth system.
    AbstractBaseUser gives us password hashing for free!
    """
    class Roles(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        VENDOR = 'vendor', 'Vendor'
        AGENT = 'agent', 'Delivery Agent'
        CUSTOMER = 'customer', 'Customer'
    
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Role as choices instead of ForeignKey for simplicity (can change to FK later)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.CUSTOMER)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Required for admin access
    
    # Django uses USERNAME_FIELD for login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_full_name(self):
        """Django admin & other code expects this method."""
        return self.full_name

    def get_short_name(self):
        return self.first_name
    


class UserAddress(models.Model):
    """
    Matches your SQL: user_addresses with POINT for coordinates
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='addresses'  # This lets you do user.addresses.all()
    )
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    coordinates = PointField(geography=True, null=True, blank=True)  # PostGIS POINT
    is_default = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'user_addresses'
    
    def __str__(self):
        return f"{self.address_line}, {self.city}"