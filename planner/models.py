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
    term = models.CharField(max_length=20, default='')   # NEW — e.g. "Dec 2025"
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

class PlanSetting(models.Model):
    importance_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.40)
    difficulty_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.35)
    frequency_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.25)
    revision_percent = models.DecimalField(max_digits=4, decimal_places=1, default=20.0)

    class Meta:
        db_table = 'plan_setting'

    def __str__(self):
        return f"Settings (revision={self.revision_percent}%)"

class Plan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateField()
    exam_date = models.DateField()
    daily_hours = models.DecimalField(max_digits=4, decimal_places=1)
    status = models.CharField(max_length=20, default='active')  # active, completed, abandoned
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'plan'

    def __str__(self):
        return f"Plan for {self.user.username} (exam {self.exam_date})"


class StudySession(models.Model):
    SESSION_TYPES = [('learning', 'Learning'), ('revision', 'Revision')]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('completed', 'Completed'),
        ('missed', 'Missed'), ('rescheduled', 'Rescheduled'),
    ]

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='sessions')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    date = models.DateField()
    duration = models.DecimalField(max_digits=4, decimal_places=2)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='learning')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'study_session'

    def __str__(self):
        return f"{self.date} - {self.topic.name} ({self.duration}h)"
        