from django.db import models

class BinanceCredentials(models.Model):
    api_key = models.CharField(max_length=100)
    api_secret = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
