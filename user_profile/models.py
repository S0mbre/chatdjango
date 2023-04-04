from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models


class Role(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=50)
    role = models.IntegerField(default=0, help_text='0 - User; 1 - Admin, 2 - Owner')

    class Meta:
        db_table = 'roles'


class User(AbstractBaseUser):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=16)
    surname = models.CharField(max_length=32)
    login = models.CharField(max_length=24)
    password = models.CharField(max_length=1024)
    private_password = models.CharField(max_length=1024)

    blocked_times = models.IntegerField(default=0)
    unblock_date = models.DateTimeField(null=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    USERNAME_FIELD = 'login'

    class Meta:
        db_table = 'users'


class UserSession(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    refresh_token = models.CharField(max_length=256)
    access_token = models.CharField(max_length=256)
    ip = models.CharField(max_length=32, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_id')
    type = models.CharField(max_length=10, help_text='public/private')
    online = models.DateTimeField(auto_now=True)
    client = models.CharField(max_length=64)

    class Meta:
        db_table = 'user_sessions'
