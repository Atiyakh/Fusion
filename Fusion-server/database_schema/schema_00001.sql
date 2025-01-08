CREATE TABLE User(
    email VARCHAR(130),
    first_name VARCHAR(20),
    last_name VARCHAR(20),
    password VARCHAR(200),
    user_creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(100) UNIQUE,
    id INTEGER NOT NULL,
    PRIMARY KEY (id)
);