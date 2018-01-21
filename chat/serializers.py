from rest_framework import serializers

from .models import Chat

class ChatSerializer(serializers.ModelSerializer):
    """
    Serializer for chat endpoint
    """
    class Meta:
        model = Chat
        fields = ['body']

    def create(self, validated_data):
        return Chat.objects.create(**validated_data)

class MemberChatSerializer(serializers.ModelSerializer):
    """
    Serializer for chat endpoint
    """
    time_sent = serializers.SerializerMethodField()
    class Meta:
        model = Chat
        fields = ['body', 'recipient', 'sender', 'time_sent']

    def get_time_sent(self, chat):
        time_sent = chat.time_chat_sent
        return time_sent.strftime("%Y-%m-%d %H:%M:%S")
