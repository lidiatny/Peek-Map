# reviews/urls.py
from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('write/<int:restaurant_id>/', views.write_review, name='write_review'),
    path('edit/<int:review_id>/', views.edit_review, name='edit_review'),
    path('reply/<int:review_id>/', views.add_reply, name='add_reply'),
]