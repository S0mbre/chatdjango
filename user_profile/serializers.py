from rest_framework import serializers

from chat.serializers import GetChatRequestSerializer
from user_profile.models import User, UserSession


class UserSignupSerializer(serializers.ModelSerializer):
    """
    Signup Serializer
    """

    class Meta:
        model = User
        fields = ("password", 'private_password', "login", 'id', 'created_at', 'name', 'surname', 'role')


class UserSignInSerializer(serializers.ModelSerializer):
    """
    SignIn Serializer
    """

    class Meta:
        model = User
        fields = ["login", 'password']


class UserSessionSerializer(serializers.ModelSerializer):
    """
    UserSession Serializer
    """

    class Meta:
        model = UserSession
        fields = ['access_token', 'refresh_token', 'type', 'user', 'client', 'ip']


class UserSignOutSerializer(serializers.ModelSerializer):
    """
    UserSession Serializer
    """

    class Meta:
        model = User
        fields = []


class UserSerializer(serializers.ModelSerializer):
    """
    SignIn Serializer
    """

    class Meta:
        model = User
        fields = ["login", 'name', 'surname', 'created_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Update Serializer
    """

    class Meta:
        model = User
        fields = ("password", 'private_password', "login", 'id', 'created_at', 'name', 'surname', 'role')


class GetUserSessionSerializer(serializers.ModelSerializer):
    """
    UserSession Serializer
    """

    class Meta:
        model = UserSession
        fields = ['id', 'created_at', 'type', 'user', 'type', 'online', 'client', 'ip']


class GetAllUsersSerializer(serializers.ModelSerializer):
    """
    Get all users Serializer
    """
    session = serializers.SerializerMethodField()

    def get_session(self, login):
        us = UserSession.objects.filter(user__login=login).first()
        serializer = GetUserSessionSerializer(instance=us)
        return serializer.data

    class Meta:
        model = User
        fields = ['id', "login", 'name', 'surname', 'created_at', 'blocked_times', 'unblock_date', 'role', 'is_deleted',
                  'session']


class GetUserDataSerializer(serializers.ModelSerializer):
    """
    Get user data Serializer
    """
    session = serializers.SerializerMethodField()

    def get_session(self, login):
        us = UserSession.objects.filter(user__login=login).last()
        serializer = GetUserSessionSerializer(instance=us)
        return serializer.data

    class Meta:
        model = User
        fields = ['id', "login", 'name', 'surname', 'created_at', 'blocked_times', 'unblock_date', 'role', 'is_deleted',
                  'session']


class GetUserSerializer(serializers.ModelSerializer):
    """
    Get user Serializer
    """
    user = GetUserDataSerializer(many=False)

    class Meta:
        model = User
        fields = ['user']


class UsersSerializer(serializers.ModelSerializer):
    """
    Get all users Serializer
    """
    users = GetAllUsersSerializer(many=True)

    class Meta:
        model = User
        fields = ['users']


class UsersMessagesSerializer(serializers.ModelSerializer):
    """
    UsersMessagesSerializer
    """
    chats = GetChatRequestSerializer(many=True)
    user = UsersSerializer(many=True)

    class Meta:
        model = User
        fields = ['user', 'chats']
