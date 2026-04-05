from django.apps import AppConfig

class CommerceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # THIS MUST MATCH THE STRING IN INSTALLED_APPS EXACTLY
    name = 'apps.commerce' 
    verbose_name = 'Commerce'