from Fluxon.Database import Models

class User(Models.AuthorizedUser):
    username = Models.CharField(max_length=100, unique=True)
    password = Models.CharField(max_length=200)
    email = Models.CharField(max_length=130)
    user_creation_date = Models.DateTimeField(auto_now_add=True)

class Teacher(Models.Model):
    user = Models.OneToOneField(to_table=User, primary_key=True)
    name = Models.CharField(max_length=100)
    department = Models.CharField(max_length=50)

class Course(Models.Model):
    course_name = Models.CharField(max_length=100)
    course_code = Models.CharField(max_length=10)
    teacher = Models.ForeignKey(to_table=Teacher, on_delete=Models.CASCADE)

class Student(Models.Model):
    user = Models.OneToOneField(to_table=User, primary_key=True)
    name = Models.CharField(max_length=100)
    birth_date = Models.DateField()
    courses = Models.ManyToManyField(to_table=Course, through='Enrollment')

class Enrollment(Models.Model):
    student = Models.ForeignKey(to_table=Student, on_delete=Models.CASCADE)
    course = Models.ForeignKey(to_table=Course, on_delete=Models.CASCADE)
    date_enrolled = Models.DateField(auto_now_add=True)
