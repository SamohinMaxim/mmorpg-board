from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from announcements.views import register, confirmation, index, custom_logout
from django.conf import settings
from django.conf.urls.static import static
from announcements import views

urlpatterns = [
    path('', index, name='index'),
    path('announcements/', include('announcements.urls')),
    path('login/', auth_views.LoginView.as_view(
        template_name='announcements/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('register/', register, name='register'),
    path('confirmation/', confirmation, name='confirmation'),
    path('accounts/profile/', index, name='profile'),
    path('my_announcements/', views.my_announcements, name='my_announcements'),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)