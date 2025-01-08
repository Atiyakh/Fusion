CREATE TABLE User(
    email VARCHAR(130),
    password VARCHAR(200),
    user_creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(100) UNIQUE,
    id INTEGER NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE Student(
    birth_date DATE,
    name VARCHAR(100),
    user INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (user) REFERENCES User(id) ON DELETE CASCADE,
    PRIMARY KEY (user)
);

CREATE TABLE Teacher(
    department VARCHAR(50),
    name VARCHAR(100),
    user INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (user) REFERENCES User(id) ON DELETE CASCADE,
    PRIMARY KEY (user)
);

CREATE TABLE Course(
    course_code VARCHAR(10),
    course_name VARCHAR(100),
    teacher INTEGER,
    id INTEGER NOT NULL,
    FOREIGN KEY (teacher) REFERENCES Teacher(user) ON DELETE CASCADE,
    PRIMARY KEY (id)
);

CREATE TABLE Enrollment(
    course INTEGER,
    date_enrolled DATE DEFAULT CURRENT_DATE,
    student INTEGER,
    id INTEGER NOT NULL,
    FOREIGN KEY (course) REFERENCES Course(id) ON DELETE CASCADE,
    FOREIGN KEY (student) REFERENCES Student(user) ON DELETE CASCADE,
    UNIQUE (course, student),
    PRIMARY KEY (id)
);