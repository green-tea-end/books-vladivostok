from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
]