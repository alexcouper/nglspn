from django.contrib import admin

from apps.follows.models import Channel, Follow, FollowedChannel


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


@admin.register(FollowedChannel)
class FollowedChannelAdmin(admin.ModelAdmin):
    list_display = ("follow", "channel")
    list_filter = ("channel",)
    raw_id_fields = ("follow", "channel")
