from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import ClientCompany, UserProfile


# 1. Register ClientCompany so you can create companies first
@admin.register(ClientCompany)
class ClientCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')


# 2. Define an Inline view for UserProfile
# This makes the Profile fields appear INSIDE the User edit page
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Info (Company & Role)'


# 3. Extend the standard UserAdmin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    # Add 'get_company' and 'get_role' to the user list columns
    list_display = ('username', 'email', 'get_company', 'get_role', 'is_staff')

    def get_company(self, instance):
        # Safely get company name
        return instance.profile.company.name if hasattr(instance, 'profile') else '-'

    get_company.short_description = 'Company'

    def get_role(self, instance):
        # Safely get role display name
        return instance.profile.get_role_display() if hasattr(instance, 'profile') else '-'

    get_role.short_description = 'Role'


# 4. Re-register User model with the new admin configuration
admin.site.unregister(User)
admin.site.register(User, UserAdmin)