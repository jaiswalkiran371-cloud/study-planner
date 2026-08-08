from django.contrib import admin
from .models import Course, Topic, TopicDependency, PYQQuestion, StudentProfile, UserCourseRating
from .models import PlanSetting
admin.site.register(PlanSetting)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_name', 'semester', 'active')
    list_filter = ('semester', 'active')
    search_fields = ('course_code', 'course_name')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'importance', 'estimated_hours', 'learning_order')
    list_filter = ('course',)
    search_fields = ('name',)


@admin.register(PYQQuestion)
class PYQQuestionAdmin(admin.ModelAdmin):
    list_display = ('topic', 'subtopic', 'year', 'marks')
    list_filter = ('course', 'topic', 'year')
    search_fields = ('question_text', 'subtopic')


admin.site.register(TopicDependency)
admin.site.register(StudentProfile)
admin.site.register(UserCourseRating)