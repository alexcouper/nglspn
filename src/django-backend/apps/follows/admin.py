from django.contrib import admin

from apps.follows.models import Channel, Follow, FollowedChannel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "owner", "created_at")
    list_filter = ("project",)
    search_fields = ("name", "project__title", "owner__email")
    raw_id_fields = ("owner",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "followed_user", "created_at")
    list_filter = ("project",)
    search_fields = ("user__email", "project__title", "followed_user__email")
    raw_id_fields = ("user", "project", "followed_user")


@admin.register(FollowedChannel)
class FollowedChannelAdmin(admin.ModelAdmin):
    list_display = ("follow", "channel")
    list_filter = ("channel",)
    raw_id_fields = ("follow", "channel")
