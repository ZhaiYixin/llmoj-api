from django.db import models

# Create your models here.
class Conversation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S')

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10)  # 'system', 'user', or 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tokens = models.IntegerField(default=0)  # Token count for the message

    def __str__(self):
        return f'{self.role}: {self.content}'