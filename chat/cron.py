from datetime import datetime, timedelta

from chat.models import Message


def delete_messages():
    try:
        messages = Message.objects.filter(is_deleted=False, deleted_at__range=[(datetime.today() - timedelta(minutes=1)), datetime.today()])
        for message in messages:
            message.deleted_at = datetime.today()
            message.is_deleted = True
    except Message.DoesNotExist:
        pass