import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from chat.models import Chat
from chat.serializers import GetUserChatsSerializer, UsersChatsSerializer
from chat_backend.const import BLOCK_TIMES
from chat_backend.settings import BASE_DIR
from user_profile.models import Role
from user_profile.serializers import *

from django.contrib.auth.hashers import check_password

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
from django.contrib.auth.hashers import make_password
from datetime import datetime, timedelta


class SignupView(generics.GenericAPIView):
    serializer_class = UserSignupSerializer

    def post(self, request):

        request.POST._mutable = True
        try:
            role = Role.objects.get(id=request.data['role'])
        except Role.DoesNotExist:
            return Response(status=status.HTTP_200_OK,
                            data={"data": None, "code": status.HTTP_400_BAD_REQUEST, "status": 1,
                                  "message": "role not found"})
        if 'role' not in request.data:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None, "code": status.HTTP_400_BAD_REQUEST, "status": 0,
                                  "message": "role required"})
        elif 'password' not in request.data:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None, "code": status.HTTP_400_BAD_REQUEST, "status": 0,
                                  "message": "password required"})
        elif 'private_password' not in request.data:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None, "code": status.HTTP_400_BAD_REQUEST, "status": 0,
                                  "message": "private_password required"})
        request.data["role"] = role.id
        request.data['password'] = make_password(request.data['password'])
        request.data['private_password'] = make_password(request.data['private_password'])
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(login=request.data["login"], is_deleted=False)
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None, "code": status.HTTP_400_BAD_REQUEST, "status": 0,
                                      "message": "user with this login already created"})
            except User.DoesNotExist:
                pass
            serializer.save()
            user = User.objects.get(id=serializer.data['id'])
            user.save()
            return Response(status=status.HTTP_201_CREATED,
                            data={"data": None, "code": status.HTTP_201_CREATED, "status": 201,
                                  "message": "ok"})
        return Response(status=status.HTTP_400_BAD_REQUEST,
                        data={"data": serializer.errors, "code": status.HTTP_400_BAD_REQUEST, "status": 1,
                              "message": "data not valid"})


class SignInView(generics.GenericAPIView):
    serializer_class = UserSignInSerializer

    def post(self, request, format=None):
        """
        SignIn
        :param client
        """
        user = None
        try:
            password = request.data['password']
            serializer = UserSignInSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    user = User.objects.get(login=serializer.data.get('login'), is_deleted=False)
                    print('user', user)
                    user_session = UserSession.objects.filter(user=user, is_active=True, online__range=[
                        (datetime.today() - timedelta(minutes=10)), datetime.today()])
                    if user_session.count() > 0:
                        return Response(status=status.HTTP_400_BAD_REQUEST,
                                        data={"data": None,
                                              "code": status.HTTP_400_BAD_REQUEST,
                                              "message": 'user already has active session'})
                    else:
                        UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
                except UserSession.DoesNotExist:
                    return Response(status=status.HTTP_400_BAD_REQUEST,
                                    data={"data": None,
                                          "code": status.HTTP_400_BAD_REQUEST,
                                          "message": 'user not found'})
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": serializer.errors,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'user not found'})
            if check_password(password, user.password):
                request.data['type'] = 'public'
            elif check_password(password, user.private_password):
                request.data['type'] = 'private'
            else:
                user.blocked_times += 1
                minutes = 0
                if user.blocked_times < len(BLOCK_TIMES):
                    minutes = BLOCK_TIMES[user.blocked_times]
                else:
                    minutes = BLOCK_TIMES[len(BLOCK_TIMES) - 1]
                user.unblock_date = datetime.today() + timedelta(minutes=minutes)
                user.save()
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'invalid password'})

            if user.unblock_date is not None and user.unblock_date.time() > datetime.now().time():
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'You are blocked, please try later'})
            from_field = request.data['from']
            if from_field == 'admin' and user.role.id == 1:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'You are not an admin'})
            if from_field == 'default' and user.role.id != 1:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'You are not a default user'})
            token = RefreshToken.for_user(user)
            access_token = str(token.access_token)
            refresh_token = str(token)
            request.data['access_token'] = access_token
            request.data['refresh_token'] = refresh_token
            request.data['user'] = user.id
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                request.data['ip'] = x_forwarded_for.split(',')[-1].strip()
            else:
                request.data['ip'] = request.META.get('REMOTE_ADDR')

            session_serializer = UserSessionSerializer(data=request.data)
            if session_serializer.is_valid():
                session_serializer.save()
                result = {'access_token': access_token, 'refresh_token': refresh_token}
                return Response(status=status.HTTP_200_OK,
                                data={"data": result,
                                      "code": status.HTTP_200_OK,
                                      "message": 'ok'})
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": session_serializer.errors,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'not valid'})
        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'user not found'})


class SignOutView(generics.GenericAPIView):
    """
    SignOut
    """

    def post(self, request, format=None):
        try:
            id = AccessToken(request.headers.get('Authorization'))['user_id']
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                            data={"data": None,
                                  "code": status.HTTP_401_UNAUTHORIZED,
                                  "message": 'Token is invalid or expired'})
        try:
            user = User.objects.get(id=id, is_deleted=False)
            try:
                UserSession.objects.filter(user_id=user.id, is_active=True).update(is_active=False)
            except UserSession.DoesNotExist:
                pass

        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'user not found'})
        return Response(status=status.HTTP_201_CREATED,
                        data={"data": None,
                              "code": status.HTTP_201_CREATED,
                              "message": 'ok'})


class MyUserView(generics.GenericAPIView):
    """
    User Actions
    """
    serializer_class = UserUpdateSerializer

    def get(self, request):
        try:
            user_id = AccessToken(request.headers.get('Authorization'))['user_id']
            try:
                print(user_id)
                user = User.objects.get(id=user_id)
            except:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'User not found'})
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                        data={"data": None,
                              "code": status.HTTP_401_UNAUTHORIZED,
                              "message": 'Token is invalid or expired'})
        user = GetUserSerializer(instance={'user': user})
        return Response(status=status.HTTP_200_OK,
                        data={"data": user.data, "code": status.HTTP_200_OK, "status": 1, "message": 'ok'})

    def delete(self, request):
        try:
            my_id = AccessToken(request.headers.get('Authorization'))['user_id']
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                            data={"data": None,
                                  "code": status.HTTP_401_UNAUTHORIZED,
                                  "message": 'Token is invalid or expired'})
        try:
            target_user = User.objects.get(id=my_id, is_deleted=False)
            target_user.is_deleted = True
            target_user.save()
        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'user not found'})
        return Response(status=status.HTTP_201_CREATED,
                        data={"data": None,
                              "code": status.HTTP_201_CREATED,
                              "message": 'ok'})


    def put(self, request):
        """
        update user
        """
        try:
            user_id = AccessToken(request.headers.get('Authorization'))['user_id']
            try:
                print(user_id)
                user = User.objects.get(id=user_id)
            except:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'User not found'})
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                        data={"data": None,
                              "code": status.HTTP_401_UNAUTHORIZED,
                              "message": 'Token is invalid or expired'})
        if 'password' in request.data:
            request.data['password'] = make_password(request.data['password'])


        if 'private_password' in request.data:
            request.data['private_password'] = make_password(request.data['private_password'])


        request.data['id'] = user_id
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_200_OK,
                            data={"data": serializer.data, "code": status.HTTP_200_OK, "status": 1, "message": 'ok'})
        return Response(status=status.HTTP_400_BAD_REQUEST,
                        data={"data": serializer.errors, "code": status.HTTP_400_BAD_REQUEST, "status": 0,
                              "message": 'failed'})

class UserView(generics.GenericAPIView):
    """
    User Actions
    """
    serializer_class = UserUpdateSerializer

    def delete(self, request, user_id, format=None):
        try:
            my_id = AccessToken(request.headers.get('Authorization'))['user_id']
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                            data={"data": None,
                                  "code": status.HTTP_401_UNAUTHORIZED,
                                  "message": 'Token is invalid or expired'})
        try:
            user = User.objects.get(id=my_id, is_deleted=False)
            target_user = User.objects.get(id=user_id, is_deleted=False)
            print(user.role, target_user.role)
            if user.role.role > target_user.role.role:
                target_user.is_deleted = True
                target_user.save()
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'not enough permissions'})
        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'user not found'})
        return Response(status=status.HTTP_201_CREATED,
                        data={"data": None,
                              "code": status.HTTP_201_CREATED,
                              "message": 'ok'})


    def put(self, request, user_id, format=None):
        """
        update user
        """
        try:
            my_id = AccessToken(request.headers.get('Authorization'))['user_id']
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                            data={"data": None,
                                  "code": status.HTTP_401_UNAUTHORIZED,
                                  "message": 'Token is invalid or expired'})
        try:
            target_user = User.objects.get(id=user_id)
            user = User.objects.get(id=my_id, is_deleted=False)
        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None, "code": status.HTTP_400_BAD_REQUEST, "status": 0,
                                  "message": 'user not found'})

        serializer = UserUpdateSerializer(target_user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_200_OK,
                            data={"data": None, "code": status.HTTP_200_OK, "status": 1, "message": 'ok'})
        return Response(status=status.HTTP_400_BAD_REQUEST,
                        data={"data": serializer.errors, "code": status.HTTP_400_BAD_REQUEST, "status": 0,
                              "message": 'failed'})


class GetAllUsersView(generics.ListAPIView):
    """
    Get all users view
    """
    serializer_class = UsersSerializer

    def get(self, request, *args, **kwargs):

        try:
            user_id = AccessToken(request.headers.get('Authorization'))['user_id']
            try:
                user = User.objects.get(id=user_id)
            except:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'User not found'})
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                            data={"data": None,
                                  "code": status.HTTP_401_UNAUTHORIZED,
                                  "message": 'Token is invalid or expired'})
        users = User.objects.filter(~Q(user_id=user_id), is_deleted=False).all()
        paginator = Paginator(users, 20)
        page = 1
        if 'page' in request.data:
            page = request.data['page']
        users = UsersSerializer(instance={'users': paginator.page(page)})
        return Response(status=status.HTTP_200_OK,
                        data={"data": users.data, "code": status.HTTP_200_OK, "status": 200,
                              "message": "ok"})


class SearchUsersAndChat(generics.ListAPIView):
    """
    Get all users by query
    """
    serializer_class = UsersSerializer

    def get(self, request, *args, **kwargs):

        try:
            user_id = AccessToken(request.headers.get('Authorization'))['user_id']
            try:
                user = User.objects.get(id=user_id)
            except:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'User not found'})
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                            data={"data": None,
                                  "code": status.HTTP_401_UNAUTHORIZED,
                                  "message": 'Token is invalid or expired'})
        search = request.GET.get('text', '')
        print(search)
        users = User.objects.filter(~Q(user_id=user_id), is_deleted=False, login__icontains=search).all()
        chats = Chat.objects.filter(title__icontains=search).all()
        user_paginator = Paginator(users, 50)
        chat_paginator = Paginator(chats, 50)
        page = 1
        if 'page' in request.data:
            page = request.data['page']
        users = UsersSerializer(instance={'users': user_paginator.page(page)})
        chats = UsersChatsSerializer(instance={'chats': chat_paginator.page(page)})

        return Response(status=status.HTTP_200_OK,
                        data={"data": {'user': users.data, 'chats': chats.data}, "code": status.HTTP_200_OK,
                              "status": 200,
                              "message": "ok"})
