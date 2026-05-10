from django.contrib import admin
from .models import Announcement, Response, NewsLetter

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'created_at', 'updated_at')
    list_filter = ('category', 'created_at', 'author')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'content', 'category')
        }),
        ('Автор и даты', {
            'fields': ('author', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('announcement', 'author', 'is_accepted', 'created_at')
    list_filter = ('is_accepted', 'created_at', 'announcement__category')
    search_fields = ('text', 'announcement__title', 'author__username')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    actions = ['mark_as_accepted']

    def mark_as_accepted(self, request, queryset):
        updated_count = 0
        for response in queryset:
            if not response.is_accepted:
                response.accept_response()
                updated_count += 1
        self.message_user(request, f'{updated_count} откликов было принято и авторы получили уведомления.')
    mark_as_accepted.short_description = "Принять выбранные отклики"

@admin.register(NewsLetter)
class NewsLetterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sent_at', 'recipient_count')
    readonly_fields = ('sent_at', 'recipients')

    def recipient_count(self, obj):
        return obj.recipients.count()
    recipient_count.short_description = 'Количество получателей'

    actions = ['send_newsletter_again']

    def send_newsletter_again(self, request, queryset):
        sent_count = 0
        for newsletter in queryset:
            newsletter.send_to_all_users()
            sent_count += 1
        self.message_user(
            request,
            f'{sent_count} рассылок были отправлены повторно всем пользователям.'
        )
    send_newsletter_again.short_description = "Отправить выбранные рассылки повторно"
