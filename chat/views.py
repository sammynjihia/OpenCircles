from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework import status
from rest_framework.response import Response

from .models import Chat
from .serializers import *
# Create your views here.

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def save_chat(request):
    serializer = ChatSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save(owner=request.user.member, recipient="opencircles")
            data = {"status":1}
        except Exception as e:
            data = {"status":0, "message":"Unable to send chat"}
        return Response(data, status=status.HTTP_200_OK)
    data = {"status":0, "message":serializer.errors}
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def retrieve_chat(request):
    chats = Chat.objects.filter(owner=request.user.member)
    try:
        member_chat_serializer = MemberChatSerializer(chats, many=True)
        data = {"status":1, "chats":member_chat_serializer.data}
    except Exception as e:
        data = {"status":0, "message":"Unable to retrieve chats"}
    return Response(data, status=status.HTTP_200_OK)
