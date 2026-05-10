from django.contrib.auth import login
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from .models import Announcement, Response, NewsLetter, MediaFile, logger
from .forms import AnnouncementForm, ResponseForm, NewsLetterForm, CustomUserCreationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import random
from django.template.loader import render_to_string
from django.utils import timezone
import re
from django.contrib.auth import logout


logger = logging.getLogger(__name__)


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Сохраняем пользователя, но не активируем сразу
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Генерируем код подтверждения
            confirmation_code = str(random.randint(100000, 999999))

            # Сохраняем код в сессии
            request.session['confirmation_code'] = confirmation_code
            request.session['user_id_to_activate'] = user.id

            # Отправляем письмо
            try:
                email_content = render_to_string('registration/confirmation_email.html', {
                    'username': user.username,
            'confirmation_code': confirmation_code,
                })

                send_mail(
                    'Код подтверждения регистрации',
            email_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
            html_message=email_content
                )
                messages.success(request, 'Код подтверждения отправлен на ваш email')
                return redirect('confirmation')
            except Exception as e:
                print(f"Ошибка отправки письма: {e}")
                user.delete()  # Удаляем пользователя, если письмо не отправлено
                return render(request, 'announcements/register.html',
                    {'form': form, 'error': f'Ошибка отправки письма: {str(e)}'})
        else:
            # Если форма невалидна, передаём её с ошибками в шаблон
            return render(request, 'announcements/register.html', {'form': form})
    else:
        # Для гет запроса создаём пустую форму
        form = CustomUserCreationForm()

    return render(request, 'announcements/register.html', {'form': form})


def confirmation(request):
    if request.method == 'POST':
        entered_code = request.POST.get('confirmation_code')
        saved_code = request.session.get('confirmation_code')
        user_id = request.session.get('user_id_to_activate')

        # Проверяем, что все данные есть в сессии
        if not saved_code:
            messages.error(request, 'Код подтверждения не найден. Попробуйте зарегистрироваться снова.')
            return redirect('register')

        if not user_id:
            messages.error(request, 'Данные пользователя не найдены. Попробуйте зарегистрироваться снова.')
            return redirect('register')

        # Сравниваем коды
        if entered_code == saved_code:
            try:
                # Находим пользователя по айди
                user = User.objects.get(id=user_id)
                # Активируем пользователя
                user.is_active = True
                user.save()

                # Очищаем сессию
                del request.session['confirmation_code']
                del request.session['user_id_to_activate']

                messages.success(request, 'Регистрация завершена! Теперь вы можете войти.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'Пользователь не найден.')
                return redirect('register')
        else:
            messages.error(request, 'Неверный код подтверждения')
    return render(request, 'announcements/confirmation.html')



def index(request):
    announcements = Announcement.objects.all().order_by('-created_at')
    paginator = Paginator(announcements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'announcements/index.html', {'page_obj': page_obj})

def custom_logout(request):
    logout(request)  # завершаем сессию
    messages.success(request, 'Вы успешно вышли из системы!')
    return redirect('announcements:index')  # перенаправление на главную


def announcement_detail(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    responses = announcement.responses.all().order_by('-created_at')

    # Форма для добавления отклика (только для авторизованных)
    response_form = None
    if request.user.is_authenticated:
        if request.method == 'POST':
            response_form = ResponseForm(request.POST)
            if response_form.is_valid():
                response = response_form.save(commit=False)
                response.announcement = announcement
                response.author = request.user
                response.save()
                messages.success(request, 'Отклик отправлен! Автор получит уведомление.')
                return redirect('announcements:announcement_detail', pk=announcement.pk)
        else:
            response_form = ResponseForm()

    return render(request, 'announcements/announcement_detail.html', {
        'announcement': announcement,
        'responses': responses,
        'response_form': response_form
    })



@login_required
def create_announcement(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.save()

            # Обработка файлов напрямую из request.FILES
            media_files = request.FILES.getlist('media_files')
            file_errors = []
            for uploaded_file in media_files:
                try:
                    MediaFile.objects.create(
                announcement=announcement,
                file=uploaded_file
            )
                except Exception as e:
                    file_errors.append(f'Ошибка загрузки {uploaded_file.name}: {str(e)}')

            if file_errors:
                for error in file_errors:
                    messages.error(request, error)
            else:
                messages.success(request, 'Объявление успешно создано!')

            return redirect('my_announcements')
        else:
            print("Ошибки формы:", form.errors)
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = AnnouncementForm()
    return render(request, 'announcements/create_announcement.html', {'form': form})



@login_required
def edit_announcement(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk, author=request.user)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Объявление успешно обновлено!')
            return redirect('my_announcements')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'announcements/edit_announcement.html', {'form': form, 'announcement': announcement})


@login_required
def my_announcements(request):
    announcements = Announcement.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'announcements/my_announcements.html', {
        'announcements': announcements
    })


@login_required
def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id, author=request.user)

    if request.method == 'POST':
        announcement.delete()
        messages.success(request, 'Объявление успешно удалено!')
        return redirect('announcements:my_announcements')

    return redirect('announcements:my_announcements')

@login_required
def announcement_responses(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)

    if announcement.author != request.user:
        messages.error(request, 'У вас нет доступа к откликам этого объявления.')
        return redirect('announcements:announcement_detail', pk=pk)

    # Получаем все отклики
    all_responses = announcement.responses.all()
    total_count = all_responses.count()

    # Считаем принятые отклики
    accepted_responses = all_responses.filter(is_accepted=True)
    accepted_count = accepted_responses.count()

    # Считаем ожидающие отклики
    pending_responses = all_responses.filter(is_accepted=False)
    pending_count = pending_responses.count()

    # Применяем фильтрацию по статусу
    status_filter = request.GET.get('status')
    if status_filter == 'accepted':
        responses = accepted_responses
    elif status_filter == 'pending':
        responses = pending_responses
    else:
        responses = all_responses

    # Сортировка
    responses = responses.order_by('-created_at')

    return render(request, 'announcements/responses.html', {
        'announcement': announcement,
        'responses': responses,
        'status_filter': status_filter,
        'total_count': total_count,
        'accepted_count': accepted_count,
        'pending_count': pending_count
    })


@login_required
def delete_response(request, response_id):
    try:
        response = get_object_or_404(Response, pk=response_id)
        announcement_pk = response.announcement.pk

        # Проверка прав: удалить может:
        # 1. Автор объявления (владелец объявления)
        # 2. Автор отклика (только если отклик не принят)
        if (response.announcement.author != request.user and
            (response.author != request.user or response.is_accepted)):
            messages.error(request, 'У вас нет прав для удаления этого отклика.')
            return redirect('announcements:announcement_responses', pk=announcement_pk)

        response.delete()
        messages.success(request, 'Отклик успешно удалён!')

    except Response.DoesNotExist:
        messages.error(request, 'Отклик не найден.')
        return redirect('announcements:index')
    except Exception as e:
        logger.error(f'Ошибка удаления отклика {response_id}: {e}')
        messages.error(request, f'Произошла ошибка при удалении отклика: {str(e)}')
        return redirect('announcements:announcement_responses', pk=announcement_pk)

    return redirect('announcements:announcement_responses', pk=announcement_pk)



@login_required
def accept_response(request, response_id):
    try:
        response = get_object_or_404(Response, pk=response_id)

        # Только автор объявления может принимать отклики
        if response.announcement.author != request.user:
            messages.error(request, 'У вас нет прав для принятия этого отклика.')
            return redirect('announcements:announcement_detail', pk=response.announcement.pk)

        if response.is_accepted:
            messages.warning(request, 'Этот отклик уже принят.')
            return redirect('announcements:announcement_responses', pk=response.announcement.pk)

        response.is_accepted = True
        response.save()
        messages.success(request, 'Отклик успешно принят! Уведомление отправлено автору отклика.')

        # Отправка уведомления автору отклика
        response.send_acceptance_notification()

    except Exception as e:
        logger.error(f'Ошибка принятия отклика {response_id}: {e}')
        messages.error(request, f'Произошла ошибка при принятии отклика: {str(e)}')

    return redirect('announcements:announcement_responses', pk=response.announcement.pk)



@login_required
def add_response(request, announcement_id):
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    if request.method == 'POST':
        form = ResponseForm(request.POST)
        if form.is_valid():
            response = form.save(commit=False)
            response.announcement = announcement
            response.author = request.user
            response.save()
            messages.success(request, 'Отклик отправлен! Автор получит уведомление.')
            return redirect('index')
    else:
        form = ResponseForm()
    return render(request, 'announcements/add_response.html', {
        'form': form,
        'announcement': announcement
    })


@login_required
def send_newsletter(request):
    if not request.user.is_staff:  # Только для администраторов
        return HttpResponseForbidden("У вас нет прав для отправки рассылок")

    if request.method == 'POST':
        form = NewsLetterForm(request.POST)
        if form.is_valid():
            newsletter = form.save()
            newsletter.send_to_all_users()
            messages.success(request, 'Рассылка отправлена всем пользователям!')
            return redirect('index')
    else:
        form = NewsLetterForm()
    return render(request, 'announcements/send_newsletter.html', {'form': form})
