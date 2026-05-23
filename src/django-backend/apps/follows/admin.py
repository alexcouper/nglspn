from django.contrib import admin

from apps.follows.models import Channel, Follow, FollowChannelPreference


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "created_at")
    list_filter = ("project",)
    search_fields = ("name", "project__title")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "created_at")
    list_filter = ("project",)
    search_fields = ("user__email", "project__title")
    raw_id_fields = ("user", "project")


@admin.register(FollowChannelPreference)
class FollowChannelPreferenceAdmin(admin.ModelAdmin):
    list_display = ("follow", "channel", "email_enabled", "in_app_enabled")
    list_filter = ("channel", "email_enabled", "in_app_enabled")
    raw_id_fields = ("follow", "channel")
