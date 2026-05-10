from django.urls import path
from . import views

app_name = 'announcements'

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.announcement_detail, name='announcement_detail'),
    path('create/', views.create_announcement, name='create_announcement'),
    path('edit/<int:pk>/', views.edit_announcement, name='edit_announcement'),
    path('delete/<int:announcement_id>/', views.delete_announcement, name='delete_announcement'),
    path('my/', views.my_announcements, name='my_announcements'),
    path('response/<int:response_id>/accept/', views.accept_response, name='accept_response'),
    path('response/<int:response_id>/delete/', views.delete_response, name='delete_response'),
    path('announcement/<int:pk>/responses/', views.announcement_responses, name='announcement_responses'),
    path('announcement/<int:announcement_id>/add-response/', views.add_response, name='add_response'),
    path('send-newsletter/', views.send_newsletter, name='send_newsletter'),
]
