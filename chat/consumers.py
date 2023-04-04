import datetime
import json
from time import gmtime

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from user_profile.models import User
from .models import Chat, Message
from .serializers import *
from django.db.models import Q


class ChatConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.chat_id = None
        self.chat = None
        self.user = None

    def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat = Chat.objects.get(pk=self.chat_id)
        # connection has to be accepted
        self.accept()

        try:
            token = str(self.scope['query_string']).split('=')[1][:-1]
            user_id = AccessToken(token)['user_id']
        except:
            # invalid token
            self.send(json.dumps({
                "data": None,
                "code": status.HTTP_400_BAD_REQUEST,
                "message": 'invalid token'
            }))
            self.close(3000)
            return
        try:
            self.user = User.objects.get(id=user_id)
        except:
            self.send(json.dumps({
                "data": None,
                "code": status.HTTP_400_BAD_REQUEST,
                "message": 'user not found'
            }))
            self.close(3001)
            return

        # join the room group
        async_to_sync(self.channel_layer.group_add)(
            self.chat_id,
            self.channel_name
        )
        self.read_all(token)
        # send the user list to the newly joined user
        messages = Message.objects.filter(chat__id=self.chat_id, is_deleted=False).all()
        paginator = Paginator(messages, 50)
        total = messages.count()
        messages = MessagesSerializer(instance={'messages': paginator.page(1), 'total': total})
        self.send(json.dumps({
            'messages': messages.data,
        }))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.chat_id,
            self.channel_name
        )

    def receive(self, text_data=None, bytes_data=None):
        try:
            text_data_json = json.loads(text_data)
            self.read_all(text_data_json['content']['access_token'])
            event = text_data_json['event']
            print(event)
            if event == 'create_message':
                self.create_message(text_data_json)
                async_to_sync(self.channel_layer.group_send)(
                    self.chat_id,
                    {
                        'user': self.user.id,
                        'type': 'last_message',
                        'editable': False,
                        'deleted': False,
                    }
                )
            elif event == 'delete_message':
                self.delete_message(text_data_json)
                async_to_sync(self.channel_layer.group_send)(
                    self.chat_id,
                    {
                        'user': self.user.id,
                        'type': 'last_message',
                        'editable': False,
                        'deleted': True,
                    }
                )
            elif event == 'edit_message':
                self.edit_message(text_data_json)
                async_to_sync(self.channel_layer.group_send)(
                    self.chat_id,
                    {
                        'user': self.user.id,
                        'type': 'last_message',
                        'editable': True,
                        'deleted': False,
                    }
                )
        except Exception as e:
            print('Exception', e)
            return

    def read_all(self, access_token):
        try:
            user_id = AccessToken(access_token)['user_id']
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
        for message in Message.objects.filter(chat__id=self.chat_id, is_deleted=False):
            data = {'message': message.id, 'is_read': True, 'user': user.id}
            serializer = CreateMessageStatusSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                self.send(text_data=json.dumps({
                    "data": serializer.errors,
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": 'failed'
                }))
                return
        self.send(text_data=json.dumps({
            "data": None,
            "code": status.HTTP_201_CREATED,
            "message": 'reading completed'
        }))

    def last_message(self, data):
        editable = data["editable"]
        deleted = data["deleted"]
        print(editable, deleted)
        if editable:
            message = Message.objects.filter(chat__id=self.chat_id, is_deleted=False, updated_at__isnull=False).order_by('updated_at').last()
        elif deleted:
            message = Message.objects.filter(chat__id=self.chat_id, is_deleted=True).order_by('deleted_at').last()
        else:
            message = Message.objects.filter(chat__id=self.chat_id, is_deleted=False).order_by('created_at').last()

        serializer = SingleMessageSerializer(instance={'message': message})
        self.send(text_data=json.dumps({
            "data": serializer.data,
            "code": status.HTTP_200_OK,
            "message": 'ok'
        }))
        self.channel_layer.group_send(
            self.chat_id,
            {
                "data": serializer.data,
                "code": status.HTTP_200_OK,
                "message": 'ok'
            }
        )

    def create_message(self, event):
        content = event['content']
        text = content["text"]
        print('create_message')
        try:
            user_id = AccessToken(content['access_token'])
        except:
            # invalid token
            print('create_message invalid token')
            self.send(json.dumps({
                "data": None,
                "code": status.HTTP_400_BAD_REQUEST,
                "message": 'invalid token'
            }))
            return
        content['chat'] = self.chat_id
        serializer = CreateMessageSerializer(data=user_id)
        if serializer.is_valid():
            serializer.save()
            message = Message.objects.get(id=serializer.data['id'])
            print('create_message  serializer.save()', message)
            if 'media' in content:
                for media in content['media']:
                    print(f'media  {media}',  serializer.data)
                    try:
                        media = Media.objects.get(id=media['id'])
                        print('media', media)
                        media.message_id = serializer.data['id']
                        media.save()
                        print(f'media try {media}')
                    except:
                        print('Media.DoesNotExist')
                        self.send(text_data=json.dumps({
                            "data": None,
                            "code": status.HTTP_400_BAD_REQUEST,
                            "message": 'media not found'
                        }))
                        return
                print('media_serializer  CreateMediaSerialize 1')
                media_serializer = CreateMediaSerializer(data=content)
                print('media_serializer  CreateMediaSerializer.save() 2')
                if not media_serializer.is_valid():
                    print('create_message media_serializer.errors', media_serializer.errors)
                    self.send(text_data=json.dumps({
                        "data": media_serializer.errors,
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": 'cannot create media'
                    }))
                    return
        else:
            print('create_message serializer.errors', serializer.errors)
            self.send(text_data=json.dumps({
                "data": serializer.errors,
                "code": status.HTTP_400_BAD_REQUEST,
                "message": 'failed'
            }))
            return
        print('create_message  fixed')
        self.send(text_data=json.dumps({
            "data": None,
            "code": status.HTTP_201_CREATED,
            "message": 'ok'
        }))

    def delete_message(self, event):
        content = event['content']
        id = content["id"]
        when = content['when']
        try:
            message = Message.objects.get(id=id, is_deleted=False)
            if when == 'now':
                message.deleted_at = datetime.datetime.now()
                message.is_deleted = True
            else:
                message.deleted_at = datetime.datetime.strptime(when, "%m/%d/%Y %H:%M:%S")
            message.save()
        except Message.DoesNotExist:
            self.send(json.dumps({
                "data": None,
                "code": status.HTTP_400_BAD_REQUEST,
                "message": 'message not found'
            }))
            return

        self.send(text_data=json.dumps({
            "data": None,
            "code": status.HTTP_201_CREATED,
            "message": 'ok'
        }))

    def edit_message(self, event):
        content = event['content']
        text = content["text"]
        message_id = content['id']

        message = Message.objects.get(id=message_id, is_deleted=False)
        message.text = text
        message.updated_at = datetime.datetime.now()
        message.save()

    def pin_message(self, event):
        content = event['content']
        id = content["id"]
        pinned = None
        try:
            message = Message.objects.get(id=id, is_deleted=False)
            message.pinned = not message.pinned
            pinned = message.pinned
            message.save()
        except Message.DoesNotExist:
            self.send(json.dumps({
                "data": None,
                "code": status.HTTP_400_BAD_REQUEST,
                "message": 'message not found'
            }))
            return
        self.send(text_data=json.dumps({
            "data": pinned,
            "code": status.HTTP_201_CREATED,
            "message": 'ok'
        }))
