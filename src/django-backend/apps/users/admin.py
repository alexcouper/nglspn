from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "full_name",
        "is_verified",
        "is_active",
        "is_staff",
        "created_at",
        "kennitala",
        "discussion_email_frequency",
        "article_email_frequency",
    )
    list_filter = (
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "discussion_email_frequency",
        "article_email_frequency",
        "created_at",
    )
    search_fields = ("email", "first_name", "last_name", "kennitala")
    ordering = ("-created_at",)
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "kennitala")}),
        (
            _("Email preferences"),
            {
                "fields": (
                    "discussion_email_frequency",
                    "article_email_frequency",
                ),
            },
        ),
        (_("Privacy"), {"fields": ("opt_in_to_external_promotions",)}),
        (
            _("Articles"),
            {
                "fields": ("article_trust",),
                "description": _(
                    "When unchecked, this user's published articles render "
                    "locally on their project page but stay out of global "
                    "surfaces until an admin approves each one."
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
        (_("System"), {"fields": ("id",)}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "kennitala", "password1", "password2"),
            },
        ),
    )

    @admin.display(description="Full Name")
    def full_name(self, obj: User) -> str:
        return obj.full_name
