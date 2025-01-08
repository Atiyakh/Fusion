from Fluxon.Database import Models
from models import User

class Owner(Models.Model):
    user = Models.OneToOneField(User, on_delete=Models.CASCADE)
    storage_limit = Models.BigIntegerField(default=10 * 1024 * 1024 * 1024)

class Directory(Models.Model):
    name = Models.CharField(max_length=255)
    directory = Models.ForeignKey('Directory', on_delete=Models.CASCADE)
    owner = Models.ForeignKey(Owner, on_delete=Models.CASCADE)
    created_at = Models.DateTimeField(auto_now_add=True)

class File(Models.Model):
    name = Models.CharField(max_length=255)
    directory = Models.ForeignKey(Directory, on_delete=Models.CASCADE)
    owner = Models.ForeignKey(Owner, on_delete=Models.CASCADE)
    size = Models.BigIntegerField()
    file_type = Models.CharField(max_length=50)
    created_at = Models.DateTimeField(auto_now_add=True)
    updated_at = Models.DateTimeField(auto_now=True)

class FileMetadata(Models.Model):
    file = Models.OneToOneField(File, on_delete=Models.CASCADE)
    is_encrypted = Models.BooleanField(default=False)
    encryption_algorithm = Models.CharField(max_length=100, null=True)
    last_accessed_at = Models.DateTimeField(auto_now=True)
