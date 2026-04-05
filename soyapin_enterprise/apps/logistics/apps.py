from django.apps import AppConfig


class LogisticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.logistics'
    verbose_name = 'Logistics & Delivery'



    def ready(self):
        import apps.logistics.signals