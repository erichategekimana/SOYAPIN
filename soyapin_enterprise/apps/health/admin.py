from django.contrib import admin
from .models import HealthProfile

@admin.register(HealthProfile)
class HealthProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'dietary_goal', 'daily_protein_goal_g', 'activity_level']
    search_fields = ['user__email']
    list_filter = ['dietary_goal', 'activity_level']