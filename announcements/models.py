from django.conf import settings
from django.contrib import messages
from django.db import models
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

CATEGORY_CHOICES = [
    ('tanks', 'Танки'),
    ('healers', 'Хилы'),
    ('dd', 'ДД'),
    ('traders', 'Торговцы'),
    ('guild_masters', 'Гилдмастеры'),
    ('quest_givers', 'Квестгиверы'),
    ('blacksmiths', 'Кузнецы'),
    ('leatherworkers', 'Кожевники'),
    ('potion_makers', 'Зельевары'),
    ('spell_masters', 'Мастера заклинаний'),
]

class Announcement(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Текст объявления')
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name='Категория'
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Автор')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        indexes = [
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
        ]

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('announcements:announcement_detail', kwargs={'pk': self.pk})

class Response(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authored_responses'
    )
    text = models.TextField(verbose_name='Текст отклика')
    is_accepted = models.BooleanField(default=False, verbose_name='Принят')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    def __str__(self):
        return f'Отклик от {self.author.username} на {self.announcement.title}'

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new:
            self.send_notification()

    def send_notification(self):
        try:
            if not self.announcement.author.email:
                logger.warning(f'У автора объявления нет email: {self.announcement.author}')
                return

            subject = f'Новый отклик на ваше объявление "{self.announcement.title}"'
            message = render_to_string('emails/response_notification.html', {
                'response': self,
                'announcement': self.announcement,
            })
            plain_message = strip_tags(message)

            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [self.announcement.author.email],
                html_message=message,
            )
        except Exception as e:
            logger.error(f'Ошибка отправки уведомления автору объявления: {e}')
            logger.error('Не удалось отправить уведомление автору объявления.')

    def accept_response(self):
        self.is_accepted = True
        self.save(update_fields=['is_accepted'])
        self.send_acceptance_notification()

    def send_acceptance_notification(self):
        """Отправляет уведомление автору отклика о принятии"""
        try:
            if not self.author.email:
                logger.warning(f'У пользователя нет email: {self.author}')
                return False

            subject = 'Ваш отклик был принят!'
            domain = getattr(settings, 'SITE_DOMAIN', 'your-site.com')

            context = {
                'response': self,
                'announcement': self.announcement,
                'domain': domain,
            }

            # Рендерим HTML‑шаблон
            html_message = render_to_string('emails/acceptance_notification.html', context)
            # Текстовая версия
            plain_message = f"""
            Здравствуйте, {self.author.username}!

            Ваш отклик на объявление "{self.announcement.title}" был принят автором.

            Текст вашего отклика:
            {self.text}

            Перейти к объявлению: https://{domain}{self.announcement.get_absolute_url()}

            С уважением,
            Команда MMORPG Доска объявлений
            """

            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [self.author.email],
                html_message=html_message,
            )
            logger.info(f'Уведомление о принятии отклика {self.id} отправлено пользователю {self.author.email}')
            return True
        except Exception as e:
            logger.error(f'Ошибка отправки уведомления пользователю: {e}')
            return False

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Отклик'
        verbose_name_plural = 'Отклики'
        indexes = [
            models.Index(fields=['announcement']),
            models.Index(fields=['author']),
            models.Index(fields=['is_accepted']),
            models.Index(fields=['created_at']),
        ]

class NewsLetter(models.Model):
    subject = models.CharField(max_length=200, verbose_name='Тема')
    content = models.TextField(verbose_name='Содержание')
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='Отправлено')
    recipients = models.ManyToManyField(User, verbose_name='Получатели')
    is_sent = models.BooleanField(default=False, verbose_name='Рассылка отправлена')

    def send_to_all_users(self):
        if self.is_sent:
            return  # Рассылка уже была отправлена

        users = User.objects.all()
        emails = [user.email for user in users if user.email]

        if emails:
            try:
                send_mail(
                    self.subject,
            self.content,
            settings.DEFAULT_FROM_EMAIL,  # используем настройки проекта
            emails,
        )
                self.recipients.set(users)
                self.is_sent = True
                self.save()
            except Exception as e:
                logger.error(f'Ошибка при отправке рассылки: {e}')

    def __str__(self):
        return self.subject

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'

class MediaFile(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='media_files'
    )
    file = models.FileField(upload_to='announcement_media/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=10, blank=True)

    def save(self, *args, **kwargs):
        # Определяем тип файла
        if self.file:
            ext = self.file.name.lower()
            if ext.endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                self.file_type = 'image'
            elif ext.endswith(('mp4', 'avi', 'mov', 'webm')):
                self.file_type = 'video'
            else:
                self.file_type = 'other'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.announcement.title} - {self.file.name}"
