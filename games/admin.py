from django.contrib import admin
from .models import Platform, Genre, Game

admin.site.register(Platform)
admin.site.register(Genre)
admin.site.register(Game)