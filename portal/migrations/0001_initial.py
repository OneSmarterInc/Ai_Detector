import uuid
from django.db import migrations,models
class Migration(migrations.Migration):
    initial=True
    dependencies=[]
    operations=[migrations.CreateModel(name='ScanJob',fields=[
        ('id',models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,serialize=False)),
        ('owner',models.CharField(max_length=64,db_index=True)),
        ('status',models.CharField(max_length=20,default='queued')),
        ('progress',models.CharField(max_length=300,default='Waiting to start')),
        ('files',models.JSONField(default=list)),('results',models.JSONField(default=list)),
        ('error',models.TextField(blank=True)),('created',models.DateTimeField(auto_now_add=True)),
        ('updated',models.DateTimeField(auto_now=True)),
    ])]
