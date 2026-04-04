import uuid
from django.db import models
from django.utils import timezone

class TimestampMixin(models.Model):
    """
    Adds created_at and updated_at to any model automatically.
    Your SQL has 'created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP'
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True  # This means it won't create its own table

class UUIDMixin(models.Model):
    """
    Uses UUID instead of sequential ID for security (harder to guess URLs)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True

class SoftDeleteMixin(models.Model):
    """
    Instead of actually deleting records (DESTRUCTIVE), we mark them as deleted.
    This keeps data for analytics/auditing.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()
    
    class Meta:
        abstract = True