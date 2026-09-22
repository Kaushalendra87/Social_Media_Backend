from django.contrib import admin

from .models import Post, Like, Comment, Reply

# Register your models here.
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "author",
        "short_caption",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "created_at",
        "updated_at",
    )

    search_fields = (
        "caption",
        "author__username",
        "author__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    def short_caption(
            self,
            obj
    ):
        if not obj.caption:
            return "(No caption)"

        if len(obj.caption) > 50:
            return (
                obj.caption[:50]
                + "..."
            )

        return obj.caption

    short_caption.short_description = "Caption"


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "post",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "post__caption",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "author",
        "post",
        "content",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "created_at",
        "updated_at",
    )

    search_fields = (
        "content",
        "author__username",
        "post__caption",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "author",
        "comment",
        "content",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "created_at",
        "updated_at",
    )

    search_fields = (
        "content",
        "author__username",
        "comment__content",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )