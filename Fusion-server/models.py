from Fluxon.Database import Models

class User(Models.AuthorizedUser):
    username = Models.CharField(max_length=100, unique=True)
    password = Models.CharField(max_length=200)
    first_name = Models.CharField(max_length=20)
    last_name = Models.CharField(max_length=20)
    email = Models.CharField(max_length=130)
    user_creation_date = Models.DateTimeField(auto_now_add=True)
