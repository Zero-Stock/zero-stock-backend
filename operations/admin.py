from django.contrib import admin
from .models import ClientCompanyRegion, WeeklyMenu, DailyCensus, ProcurementRequest, ProcurementItem

@admin.register(ClientCompanyRegion)
class ClientCompanyRegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')
    list_filter = ('company',)

@admin.register(WeeklyMenu)
class WeeklyMenuAdmin(admin.ModelAdmin):
    # Grouping by Diet Category makes it easy to see the full week plan
    list_display = ('company', 'diet_category', 'day_of_week', 'meal_time')
    list_filter = ('company', 'diet_category', 'day_of_week')
    filter_horizontal = ('dishes',) # Easy selection box
    ordering = ('company', 'diet_category', 'day_of_week', 'meal_time')

@admin.register(DailyCensus)
class DailyCensusAdmin(admin.ModelAdmin):
    # Updated to show 'region' instead of 'ward'
    list_display = ('date', 'company', 'region', 'diet_category', 'count')
    list_filter = ('company', 'date', 'region')
    list_editable = ('count',)

class ProcurementItemInline(admin.TabularInline):
    model = ProcurementItem
    readonly_fields = ('raw_material', 'total_gross_quantity', 'notes')
    extra = 0
    can_delete = False

@admin.register(ProcurementRequest)
class ProcurementRequestAdmin(admin.ModelAdmin):
    list_display = ('target_date', 'company', 'status')
    inlines = [ProcurementItemInline]