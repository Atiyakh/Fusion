from Fluxon.Routing import Router
import models, views

SERVER_SECURITY_KEY = "RsxZd5wVVml7C0H_LrbIVTDJU9kR-NwS1UxWD2lTVdY"
DATABASE_SCHEMA_DIR = r"D:\project1\Fusion-server\database_schema"
DATABASE_PATH = r"D:\project1\Fusion-server\database.sqlite3"

router = Router(
    # routing setup
    mapping={
        "signup": views.signup,
        "login": views.login
    },
    # server setup
    private_key=SERVER_SECURITY_KEY,
    database_schema_dir=DATABASE_SCHEMA_DIR,
    database_path=DATABASE_PATH,
    models=models
)