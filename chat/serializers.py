from rest_framework import serializers

from chat.models import *
from chat_backend.settings import PATH


class CreateChatSerializer(serializers.ModelSerializer):
    """
    Chat Serializer
    """

    class Meta:
        model = Chat
        fields = ['title', 'type']


class GetMembers(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name')
    user_surname = serializers.CharField(source='user.surname')
    user_login = serializers.CharField(source='user.login')

    class Meta:
        model = Member
        fields = ("id", "user", 'created_at', 'user_name', 'user_surname', 'user_login')


class GetChatSerializer(serializers.ModelSerializer):
    """
    GetChatSerializer
    """
    members = GetMembers(many=True)

    class Meta:
        model = Chat
        fields = ("id", "title", 'created_at', 'members', 'type')


class GetUserChatsSerializer(serializers.ModelSerializer):
    """
    GetChatSerializer
    """
    members = GetMembers(many=True)
    messages = serializers.SerializerMethodField(allow_null=True)

    def get_messages(self, id):
        message = Message.objects.filter(chat_id=id).last()
        serializer = GetMessageSerializer(instance=message)
        return serializer.data

    class Meta:
        model = Chat
        fields = ("id", "title", 'created_at', 'members', 'messages', 'type')

class UsersChatsSerializer(serializers.ModelSerializer):
    """
    GetChatSerializer
    """
    chats = GetUserChatsSerializer(many=True)

    class Meta:
        model = Chat
        fields = ['chats']

class GetMemberSerializer(serializers.ModelSerializer):
    """
    Member Serializer
    """
    user_name = serializers.CharField(source='user.name')
    user_surname = serializers.CharField(source='user.surname')
    user_login = serializers.CharField(source='user.login')
    class Meta:
        model = Member
        fields = ['user', 'chat', 'type', 'user_name', 'user_surname', 'user_login']

class PostMemberSerializer(serializers.ModelSerializer):
    """
    Member Serializer
    """

    class Meta:
        model = Member
        fields = ['user', 'chat', 'type']

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['chat_id']


class GetMediaSerializer(serializers.ModelSerializer):
    """
    GetMediaSerializer
    """
    url = serializers.SerializerMethodField()

    def get_url(self, file):
        path = file.file.url
        return f'{PATH}/{path}'

    class Meta:
        model = Media
        fields = ("id", 'created_at', 'file', 'url')


class GetAllMediaSerializer(serializers.ModelSerializer):
    """
    GetAllMediaSerializer
    """
    media = GetMediaSerializer(many=True)

    class Meta:
        model = Media
        fields = ['media']


class GetMessageStatusSerializer(serializers.ModelSerializer):
    """
    GetMessageStatusSerializer
    """
    user_name = serializers.CharField(source='user.name')
    user_surname = serializers.CharField(source='user.surname')

    class Meta:
        model = MessageStatus
        fields = ("id", "message", 'is_read', 'user', 'user_name', 'user_surname')


class GetMessageSerializer(serializers.ModelSerializer):
    """
    GetMessageSerializer
    """
    statuses = GetMessageStatusSerializer(many=True, allow_null=True)
    media = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.name')
    user_surname = serializers.CharField(source='user.surname')
    user_login = serializers.CharField(source='user.login')

    def get_media(self, id):
        all_media = Media.objects.filter(message_id=id).all()
        serializer = GetAllMediaSerializer(instance={'media': all_media})
        return serializer.data

    class Meta:
        model = Message
        fields = ["id", 'statuses', 'media', 'updated_at', 'user', 'user_name', 'user_surname', 'text', 'created_at',
                  'user_login', 'is_deleted', 'deleted_at']


class MessagesSerializer(serializers.Serializer):
    messages = GetMessageSerializer(many=True)
    total = serializers.IntegerField()

    class Meta:
        fields = ['messages', 'total']


class SingleMessageSerializer(serializers.Serializer):
    message = GetMessageSerializer()

    class Meta:
        fields = ['message']


class CreateMessageSerializer(serializers.ModelSerializer):
    """
    Create Message Serializer
    """

    class Meta:
        model = Message
        fields = ['user', 'chat', 'text', 'id']


class CreateMediaSerializer(serializers.ModelSerializer):
    """
    Create Media Serializer
    """

    class Meta:
        model = Media
        fields = ['id', 'message']


class CreateMessageStatusSerializer(serializers.ModelSerializer):
    """
    Create MessageStatus Serializer
    """

    class Meta:
        model = MessageStatus
        fields = ['message', 'is_read', 'user']


class GetChatRequestSerializer(serializers.ModelSerializer):
    """
    GetChatRequestSerializer
    """
    chats = GetChatSerializer(many=True, allow_null=True)

    class Meta:
        model = Chat
        fields = ['chats']
