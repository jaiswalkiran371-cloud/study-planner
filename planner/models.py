from django.db import models

class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=200)
    semester = models.IntegerField()
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'course'

    def __str__(self):
        return self.course_code


class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    importance = models.DecimalField(max_digits=4, decimal_places=1)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2)
    learning_order = models.IntegerField()

    class Meta:
        db_table = 'topic'
        unique_together = ('course', 'name')

    def __str__(self):
        return self.name


class TopicDependency(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='dependencies')
    prerequisite_topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='required_by')
    
    class Meta:
        db_table = 'topic_dependency'

class PYQQuestion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    subtopic = models.CharField(max_length=200, blank=True)
    year = models.IntegerField()
    marks = models.DecimalField(max_digits=4, decimal_places=1)
    question_text = models.TextField()

    class Meta:
        db_table = 'pyq_question'

from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    programme = models.CharField(max_length=100, default='MCA')
    semester = models.IntegerField(default=1)

    class Meta:
        db_table = 'student_profile'

    def __str__(self):
        return self.user.username


class UserCourseRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    rating = models.IntegerField()

    class Meta:
        db_table = 'user_course_rating'
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} - {self.course.course_code}: {self.rating}"