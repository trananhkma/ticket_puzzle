import uuid

from django.db import models


class Ticket(models.Model):
    token = models.UUIDField(default=uuid.uuid4)

    class Meta:
        # avoid UnorderedObjectListWarning when use Paginator
        ordering = ['id']
