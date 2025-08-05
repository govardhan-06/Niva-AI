from django.db import models
from niva_app.models.base import TimestampBase
from pgvector.django import VectorField

class Document(TimestampBase):
    content = models.TextField()
    embedding = VectorField(dimensions=3072)
    memory = models.ForeignKey('niva_app.Memory', on_delete=models.CASCADE, related_name='documents')

    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['memory']),
        ]