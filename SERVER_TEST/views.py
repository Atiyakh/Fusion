from Fluxon.Database.Manipulations import AsyncSQLiteDatabase

async_db = AsyncSQLiteDatabase(r"C:\Users\skhodari\Desktop\TESTING\SERVER_TEST\database.sqlite3")

async def signup(request):
    print(request)
    await async_db.User.Insert({
        "username": "Atiya",
        "email": "atiyaalkhodari1@gmail.com",
        "password": "Atty@kh123"
    })
