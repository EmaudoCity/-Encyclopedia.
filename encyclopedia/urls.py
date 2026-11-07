from django.urls import path

from . import views

app_name = "encyclopedia"
urlpatterns = [
    path("", views.index, name="index"),
    path("search", views.search, name="search"),
    path("new", views.new_page, name="new"),
    path("random", views.random_page, name="random"),
    path("wiki/<str:title>/edit", views.edit_page, name="edit"),
    path("wiki/<str:title>", views.entry, name="entry"),
]
