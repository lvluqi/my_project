from django.db import models

# Create your models here.


class Book(models.Model):
    id = models.IntegerField(auto_created=True,primary_key=True)
    name = models.CharField(max_length=32)
    publish = models.CharField(max_length=32)
    pub_date = models.DateTimeField()

class UserInfo(models.Model):
    username = models.CharField(max_length=32)
    sex = models.CharField(max_length=32)
    email = models.CharField(max_length=32)

class Host(models.Model):
    hostname = models.CharField(max_length=32)
    ip = models.GenericIPAddressField()
    username = models.CharField(max_length=32)
    passwd = models.CharField(max_length=32)
