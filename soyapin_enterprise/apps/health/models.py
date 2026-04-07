from django.db import models
from django.conf import settings
from infrastructure.models.abstract_models import TimestampMixin

class HealthProfile(TimestampMixin, models.Model):
    class DietaryGoal(models.TextChoices):
        WEIGHT_LOSS = 'weight_loss', 'Weight Loss'
        MUSCLE_GAIN = 'muscle_gain', 'Muscle Gain'
        MAINTENANCE = 'maintenance', 'Maintenance'
        GENERAL_HEALTH = 'general_health', 'General Health'

    class ActivityLevel(models.TextChoices):
        SEDENTARY = 'sedentary', 'Sedentary'
        LIGHT = 'light', 'Lightly Active'
        MODERATE = 'moderate', 'Moderately Active'
        VERY_ACTIVE = 'very_active', 'Very Active'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='health_profile'
    )
    dietary_goal = models.CharField(
        max_length=20,
        choices=DietaryGoal.choices,
        default=DietaryGoal.GENERAL_HEALTH
    )
    daily_protein_goal_g = models.PositiveIntegerField(
        default=60,
        help_text="Daily protein target in grams"
    )
    allergies = models.JSONField(default=list, blank=True, help_text="List of allergens, e.g., ['soy', 'gluten']")
    activity_level = models.CharField(
        max_length=20,
        choices=ActivityLevel.choices,
        default=ActivityLevel.MODERATE
    )
    # Optional: age, weight, height for more accurate goals
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'health_profiles'

    def __str__(self):
        return f"{self.user.email} - {self.daily_protein_goal_g}g/day"