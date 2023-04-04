import json
from xml.dom.minidom import Document

from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.shortcuts import render

# Create your views here.
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from chat.forms import DocumentForm
from chat.pagination import SmallPagesPagination
from chat.serializers import *
from chat_backend.settings import BASE_DIR, MEDIA_ROOT, PATH
from user_profile.models import UserSession


class ChatView(generics.GenericAPIView):
    serializer_class = CreateChatSerializer

    def post(self, request):
        request.POST._mutable = True
        try:
            user_id = AccessToken(request.headers.get('Authorization'))['user_id']
        except TokenError:
            return Response(status=status.HTTP_401_UNAUTHORIZED,
                            data={"data": None,
                                  "code": status.HTTP_401_UNAUTHORIZED,
                                  "message": 'Token is invalid or expired'})
        serializer = CreateChatSerializer(data=request.data)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'user not found'})
        if serializer.is_valid():
            chat_info = serializer.save()
            chat = Chat.objects.get(id=chat_info.id)
            print(chat.id, user.id)
            request.data['user'] = user.id
            request.data['chat'] = chat.id
            try:
                session = UserSession.objects.filter(is_active=True, user_id=user.id).first()
                request.data['type'] = session.type
            except UserSession.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'no active sessions'})
            member_serializer = PostMemberSerializer(data=request.data)
            if member_serializer.is_valid():
                member_info = member_serializer.save()
                member = Member.objects.get(id=member_info.id)

                return Response(status=status.HTTP_200_OK,
                                data={"data": GetChatSerializer(instance=chat).data,
                                      "code": status.HTTP_200_OK,
                                      "message": 'ok'})
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": member_serializer.errors,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'cannot create member'})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": serializer.errors,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'failed'})


class MemberView(generics.ListCreateAPIView):
    serializer_class = GetMemberSerializer

    def post(self, request, *args, **kwargs):
        try:
            chat = Chat.objects.get(id=kwargs['chat_id'])

        except Chat.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'chat not found'})

        for data in request.data:
            data['chat'] = chat.id
            print(data['user'])
            try:
                user = User.objects.get(login=data['user'])
                data['user'] = user.pk
            except User.DoesNotExist:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": None,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'user not found'})
            serializer = PostMemberSerializer(data=data)
            if serializer.is_valid():
                try:
                    member = Member.objects.filter(user__id=data['user'], chat__id=data['chat']).count()
                    if member > 0:
                        raise ValueError('user already added')
                    if chat.type == 'private' and chat.members.count() > 2:
                        raise ValueError('you cannot add more then 1 user in private chat')
                    serializer.save()
                except ValueError as e:
                    return Response(status=status.HTTP_400_BAD_REQUEST,
                                    data={"data": None,
                                          "code": status.HTTP_400_BAD_REQUEST,
                                          "message": e})
                except Exception as e:
                    return Response(status=status.HTTP_400_BAD_REQUEST,
                                    data={"data": None,
                                          "code": status.HTTP_400_BAD_REQUEST,
                                          "message": e})
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"data": serializer.errors,
                                      "code": status.HTTP_400_BAD_REQUEST,
                                      "message": 'failed'})
        return Response(status=status.HTTP_201_CREATED,
                        data={"data": None,
                              "code": status.HTTP_201_CREATED,
                              "message": 'ok'})

    def get(self, request, *args, **kwargs):
        try:
            members = Member.objects.filter(chat__id=kwargs['chat_id'])
            serializer = GetMemberSerializer(members, many=True)
            result = {'count': members.count(), 'members': serializer.data}
            return Response(status=status.HTTP_200_OK,
                            data={"data": result,
                                  "code": status.HTTP_200_OK,
                                  "message": 'ok'})
        except Member.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'members not found or chat doesn\'t exist'})


class UploadMedia(generics.CreateAPIView):
    def post(self, request, *args, **kwargs):
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            media = Media(file=file)
            print(media, ';', BASE_DIR, MEDIA_ROOT)
            media.save()
            print(request.build_absolute_uri(media.file.url))
            return Response(status=status.HTTP_201_CREATED,
                            data={"data": {"url": f'{PATH}{media.file.url}', "id": media.id},
                                  "code": status.HTTP_201_CREATED,
                                  "message": 'ok'})
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": form.errors,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'invalid file'})


class GetMessagesView(generics.GenericAPIView):
    serializer_class = MessageSerializer

    def get(self, request, *args, **kwargs):
        serializer = MessageSerializer(data=request.data)
        page = request.GET.get('page', 1)

        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": serializer.errors,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'failed'})
        try:
            chat = Chat.objects.get(id=kwargs['chat_id'])

        except Chat.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"data": None,
                                  "code": status.HTTP_400_BAD_REQUEST,
                                  "message": 'chat not found'})
        messages = Message.objects.filter(chat__id=kwargs['chat_id'], is_deleted=False).order_by('-created_at').all()
        paginator = Paginator(messages, 50)
        total = messages.count()
        print('page', page)
        messages = MessagesSerializer(instance={'messages': paginator.page(page), 'total': total})
        return Response(status=status.HTTP_200_OK,
                        data={"data": messages.data,
                              "code": status.HTTP_200_OK,
                              "message": 'ok'})


class GetAllUserChatView(generics.ListAPIView):
    """
    Get all user's chat view
    """
    serializer_class = MessageSerializer

    def get(self, request, *args, **kwargs):
        page = 1
        if 'page' in request.data:
            page = request.data['page']
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
        result = {}
        chats = Chat.objects.filter(members__user=user).all()
        result['chats'] = chats
        print(chats)
        messages = []
        for chat in chats:
            try:
                message = Message.objects.filter(chat__id=chat.id).last()
                print(json.dumps(message))
                messages.append(message)
            except:
                pass
        result['messages'] = messages
        serializer = GetChatRequestSerializer(instance={'chats': chats})
        # if serializer.is_valid():
        return Response(status=status.HTTP_200_OK,
                        data={"data": serializer.data,
                              "code": status.HTTP_200_OK,
                              "message": 'ok'})
        # else:
        #     return Response(status=status.HTTP_400_BAD_REQUEST,
        #                     data={"data": serializer.errors,
        #                           "code": status.HTTP_400_BAD_REQUEST,
        #                           "message": 'ok'})
