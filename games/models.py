from django.db import models
from django.contrib.auth.models import User


class Platform(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Game(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField()
    playtime_hours = models.IntegerField()
    image_url = models.URLField(blank=True, null=True)
    rating = models.FloatField(blank=True, null=True)
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-purchase_date']

    def __str__(self):
        return self.name