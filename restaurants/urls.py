# restaurants/urls.py
from django.urls import path
from . import views

app_name = 'restaurants'

urlpatterns = [
    
    # Contoh: /restaurants/detail/1
    path('detail/<int:restaurant_id>/', views.restaurant_detail, name='detail'),
    
]