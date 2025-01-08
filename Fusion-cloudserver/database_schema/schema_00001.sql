CREATE TABLE User(
    email VARCHAR(130),
    password VARCHAR(200),
    user_creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(100) UNIQUE,
    id INTEGER NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE Owner(
    storage_limit INTEGER,
    user INTEGER NOT NULL UNIQUE,
    id INTEGER NOT NULL,
    FOREIGN KEY (user) REFERENCES User(id) ON DELETE CASCADE,
    PRIMARY KEY (id)
);

CREATE TABLE Directory(
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    name VARCHAR(255),
    owner INTEGER,
    id INTEGER NOT NULL,
    FOREIGN KEY (owner) REFERENCES Owner(id) ON DELETE CASCADE,
    PRIMARY KEY (id)
);

CREATE TABLE File(
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    directory INTEGER,
    file_type VARCHAR(50),
    name VARCHAR(255),
    owner INTEGER,
    size INTEGER,
    updated_at DATETIME,
    id INTEGER NOT NULL,
    FOREIGN KEY (directory) REFERENCES Directory(id) ON DELETE CASCADE,
    FOREIGN KEY (owner) REFERENCES Owner(id) ON DELETE CASCADE,
    PRIMARY KEY (id)
);

CREATE TABLE FileMetadata(
    encryption_algorithm VARCHAR(100),
    file INTEGER NOT NULL UNIQUE,
    is_encrypted BOOLEAN NOT NULL,
    last_accessed_at DATETIME,
    id INTEGER NOT NULL,
    FOREIGN KEY (file) REFERENCES File(id) ON DELETE CASCADE,
    PRIMARY KEY (id)
);