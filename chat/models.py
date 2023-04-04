from django.db import models

from chat.validators import file_size
from user_profile.models import User

from mirage import fields
import uuid

class Chat(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=128, blank=True, null=True)
    type = models.CharField(max_length=32, help_text='group/private', null=True)
    class Meta:
        db_table = 'chats'


class Member(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='members')
    type = models.CharField(max_length=16)

    class Meta:
        db_table = 'chat_members'


class Message(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='users')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chats')
    text = fields.EncryptedTextField(max_length=4096, blank=True)
    pinned = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'messages'


class Media(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=16)
    file = models.FileField(help_text='250 mb', validators=[file_size], null=True)

    # types:
    # voice_message
    # file
    class Meta:
        db_table = 'message_media'


class MessageStatus(models.Model):
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now=True)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = 'message_status'
