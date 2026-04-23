from django.contrib import admin
from django.utils.html import format_html
from .models import DeliveryAgent, Delivery, AgentPayout




@admin.action(description='Reset total deliveries to 0')
def reset_deliveries(modeladmin, request, queryset):
    queryset.update(total_deliveries=0)
    modeladmin.message_user(request, f"Reset deliveries for {queryset.count()} agents")



@admin.register(DeliveryAgent)
class DeliveryAgentAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'assigned_zone',
        'vehicle_type',
        'status_badge',
        'rating_avg',
        'total_deliveries',
        'last_location',
        'profile_picture_preview'
    ]

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.profile_picture)
        return "No Image"
    profile_picture_preview.short_description = 'Profile Picture'

    
    list_filter = ['status', 'vehicle_type', 'assigned_zone', 'is_active']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'assigned_zone']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Work Details', {
            'fields': ('assigned_zone', 'vehicle_type', 'status', 'is_active')
        }),
        ('Performance', {
            'fields': ('rating_avg', 'total_deliveries')
        }),
        ('Location', {
            'fields': ('current_location', 'last_location_update'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'available': 'green',
            'busy': 'orange',
            'offline': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold; text-transform: uppercase;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def last_location(self, obj):
        if obj.last_location_update:
            return f"{obj.last_location_update.strftime('%Y-%m-%d %H:%M')}"
        return "Never"
    last_location.short_description = 'Last Location Update'


class DeliveryInline(admin.StackedInline):
    """For showing delivery inline with Order (if needed later)"""
    model = Delivery
    can_delete = False
    readonly_fields = ['status', 'agent', 'pickup_time', 'actual_delivery_time']


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'order_link',
        'agent_name',
        'status_badge',
        'delivery_fee',
        'pickup_time',
        'actual_delivery_time'
    ]
    
    list_filter = ['status', 'created_at', 'agent__assigned_zone']
    search_fields = ['order__id', 'agent__user__email', 'customer_comment']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order', 'agent')
        }),
        ('Status & Timing', {
            'fields': ('status', 'pickup_time', 'actual_delivery_time')
        }),
        ('Financial', {
            'fields': ('delivery_fee',)
        }),
        ('Customer Feedback', {
            'fields': ('customer_rating', 'customer_comment', 'delivery_photo'),
            'classes': ('collapse',)
        }),
    )
    
    def order_link(self, obj):
        return format_html(
            '<a href="/admin/commerce/order/{}/change/">Order #{}</a>',
            obj.order.id, obj.order.id
        )
    order_link.short_description = 'Order'
    
    def agent_name(self, obj):
        if obj.agent:
            return obj.agent.full_name
        return "Unassigned"
    agent_name.short_description = 'Agent'
    
    def status_badge(self, obj):
        colors = {
            'preparing': 'gray',
            'ready_for_pickup': 'blue',
            'picked_up': 'orange',
            'in_transit': 'purple',
            'delivered': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(AgentPayout)
class AgentPayoutAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'agent_name',
        'amount',
        'status',
        'created_at',
        'processed_at'
    ]
    
    list_filter = ['status', 'created_at']
    search_fields = ['agent__user__email', 'transaction_reference']
    actions = ['mark_completed']
    
    def agent_name(self, obj):
        return obj.agent.full_name
    agent_name.short_description = 'Agent'
    
    @admin.action(description='Mark selected payouts as completed')
    def mark_completed(self, request, queryset):
        for payout in queryset.filter(status=AgentPayout.Status.PENDING):
            payout.mark_completed(f"MANUAL-{payout.id}")
        self.message_user(request, f"Marked {queryset.count()} payouts as completed")


@admin.action(description='Assign nearest available agent')
def assign_nearest_agent(modeladmin, request, queryset):
    from apps.logistics.services import find_nearest_agent
    for delivery in queryset.filter(agent__isnull=True):
        agent = find_nearest_agent(delivery.order)
        if agent:
            delivery.agent = agent
            delivery.save()
            agent.mark_busy()
            modeladmin.message_user(request, f'Assigned agent {agent.full_name} to delivery #{delivery.id}')
        else:
            modeladmin.message_user(request, f'No agent found for delivery #{delivery.id}', level='ERROR')

class DeliveryAdmin(admin.ModelAdmin):
    # ... existing code
    actions = [assign_nearest_agent]