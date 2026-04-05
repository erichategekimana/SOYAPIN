from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Vendor, Product, Inventory

class InventoryInline(admin.StackedInline):
    model = Inventory
    can_delete = False
    verbose_name_plural = 'Inventory'
    fields = ['quantity_available', 'restock_threshold', 'expiry_date', 'batch_number']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):  # FIX: was admin.ModelView
    list_display = ['business_name', 'user', 'verification_status', 'product_count', 'created_at']
    list_filter = ['verification_status', 'created_at']
    search_fields = ['business_name', 'user__email', 'tin_number']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Active Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'vendor', 
        'category', 
        'base_price', 
        'stock_badge',
        'is_published', 
        'created_at'
    ]
    list_filter = ['is_published', 'category', 'vendor', 'created_at']
    search_fields = ['name', 'description', 'vendor__business_name']
    list_editable = ['is_published', 'base_price']
    inlines = [InventoryInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'category', 'vendor')
        }),
        ('Pricing & Media', {
            'fields': ('base_price', 'image_url')
        }),
        ('Nutritional Information', {
            'fields': ('nutritional_data',),
            'description': 'Enter as JSON: {"protein": 25, "calories": 300, "fat": 10, "carbs": 5}'
        }),
        ('Status', {
            'fields': ('is_published', 'is_deleted')
        }),
    )
    
    def stock_badge(self, obj):
        try:
            inv = obj.inventory
            if inv.quantity_available == 0:
                color = 'red'
                text = 'OUT OF STOCK'
            elif inv.needs_restock:
                color = 'orange'
                text = f'LOW ({inv.quantity_available})'
            else:
                color = 'green'
                text = f'OK ({inv.quantity_available})'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, text
            )
        except Inventory.DoesNotExist:
            return format_html('<span style="color: gray;">NO INVENTORY</span>')
    stock_badge.short_description = 'Stock Status'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):  # FIX: was admin.ModelView
    list_display = ['product', 'quantity_available', 'restock_threshold', 'needs_restock', 'expiry_date']
    list_filter = ['quantity_available', 'expiry_date']
    search_fields = ['product__name', 'batch_number']
    
    def needs_restock(self, obj):
        return obj.needs_restock
    needs_restock.boolean = True
    needs_restock.short_description = 'Needs Restock?'