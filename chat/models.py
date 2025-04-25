from django.conf import settings
from django.db import models
import tiktoken

# Create your models here.
class ConversationTemplate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='templates', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default='')
    system_message = models.TextField()
    system_message_tokens = models.IntegerField(default=0)
    initial_conversation = models.OneToOneField('Conversation', related_name='initial_template', null=True, blank=True, on_delete=models.SET_NULL)
    starters = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='conversations', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default='')
    template = models.ForeignKey(ConversationTemplate, related_name='conversations', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} - {self.user.username} - {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10)  # 'system', 'user', or 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tokens = models.IntegerField(default=0)  # Token count for the message

    def __str__(self):
        return f'{self.role}: {self.content}'

    @staticmethod
    def count_tokens(text):
        """粗略计算消息内容的 token 数量"""
        if not hasattr(Message.count_tokens, "encoding"):
            Message.count_tokens.encoding = tiktoken.encoding_for_model("gpt-4")
        tokens = Message.count_tokens.encoding.encode(text)
        return len(tokens)

    def save(self, *args, **kwargs):
        if self.tokens == 0:
            self.tokens = self.count_tokens(self.content)
        super().save(*args, **kwargs)