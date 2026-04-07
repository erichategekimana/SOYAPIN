from apps.catalog.models import Product
from apps.identity.models import User

def recommend_products(user: User, limit=10):
    """
    Rule‑based product recommendations based on user's health profile.
    Returns a list of Product objects ordered by relevance score.
    """
    profile = getattr(user, 'health_profile', None)
    if not profile:
        # No profile → return best‑selling or random published products
        return Product.objects.filter(is_published=True, is_deleted=False)[:limit]

    daily_protein_goal = profile.daily_protein_goal_g
    dietary_goal = profile.dietary_goal
    allergies = profile.allergies if isinstance(profile.allergies, list) else []

    # Start with all published, non‑deleted products
    queryset = Product.objects.filter(is_published=True, is_deleted=False)

    # Exclude allergens (if product name or category contains allergen)
    if allergies:
        for allergen in allergies:
            queryset = queryset.exclude(name__icontains=allergen)
            # Also exclude by category name if needed
            queryset = queryset.exclude(category__name__icontains=allergen)

    # Score each product
    products_with_score = []
    for product in queryset:
        score = 0
        nutritional_data = product.nutritional_data or {}
        protein = nutritional_data.get('protein', 0)
        calories = nutritional_data.get('calories', 0)

        # 1. Protein density (protein per calorie) – higher is better for weight loss
        protein_per_calorie = protein / max(calories, 1)
        score += protein_per_calorie * 10

        # 2. How close the product's protein content helps meet daily goal
        #    (products with ~20-30g protein get a boost)
        if 15 <= protein <= 30:
            score += 5
        elif protein > 30:
            score += 3

        # 3. Dietary goal adjustments
        if dietary_goal == 'weight_loss':
            # Favour low calorie, high protein
            if calories < 200:
                score += 4
            if protein_per_calorie > 0.15:
                score += 6
        elif dietary_goal == 'muscle_gain':
            # Favour high absolute protein
            score += protein / 5
        elif dietary_goal == 'maintenance':
            # Balanced
            score += (protein / 10) + (100 / max(calories, 1))

        # 4. Boost products with high ratings (if you have a rating field)
        #    Not yet implemented, skip.

        # 5. Random small factor to avoid identical scores (deterministic tie‑break)
        score += (product.id % 100) / 1000.0

        products_with_score.append((product, score))

    # Sort by score descending
    products_with_score.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in products_with_score[:limit]]