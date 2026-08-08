from datetime import date
from .models import PlanSetting
from .models import Topic, PYQQuestion, PlanSetting
from .models import Topic, TopicDependency


def get_prerequisites(topic):
    """Returns a list of Topic objects that must come before this one."""
    deps = TopicDependency.objects.filter(topic=topic).select_related('prerequisite_topic')
    return [d.prerequisite_topic for d in deps]


def is_eligible(topic, completed_or_scheduled_topic_ids):
    """
    A topic is eligible if every one of its prerequisites is already
    in the completed/scheduled set.
    """
    prereqs = get_prerequisites(topic)
    return all(p.id in completed_or_scheduled_topic_ids for p in prereqs)


def get_eligible_topics(course, completed_or_scheduled_topic_ids):
    """Returns all topics for a course that are currently eligible to schedule."""
    all_topics = Topic.objects.filter(course=course)
    return [t for t in all_topics if is_eligible(t, completed_or_scheduled_topic_ids)]

def calculate_difficulty_score(student_rating):
    """Section 11.4: difficulty = 10 - rating"""
    if not 0 <= student_rating <= 10:
        raise ValueError("Rating must be between 0 and 10.")
    return 10 - student_rating


def calculate_frequency_score(topic):
    """
    Section 12.1: how many distinct papers this topic appeared in,
    scaled to 0-10 relative to total papers available for the course.
    """
    total_papers = PYQQuestion.objects.filter(course=topic.course).values('term').distinct().count()
    papers_with_topic = PYQQuestion.objects.filter(topic=topic).values('term').distinct().count()

    if total_papers == 0:
        return 0
    return round((papers_with_topic / total_papers) * 10, 1)


def calculate_priority_score(topic, student_rating, plan_setting=None):
    """Section 12: weighted combination of importance, difficulty, frequency."""
    settings = plan_setting or PlanSetting.objects.first()
    difficulty = calculate_difficulty_score(student_rating)
    frequency = calculate_frequency_score(topic)

    priority = (
        float(settings.importance_weight) * float(topic.importance)
        + float(settings.difficulty_weight) * difficulty
        + float(settings.frequency_weight) * frequency
    )
    return round(priority, 2)

class PlanValidationError(Exception):
    pass


def calculate_time_budget(exam_date, daily_hours, today=None):
    """
    Returns a dict with study_days, total_hours, revision_hours, learning_hours.
    Mirrors Section 11.3 of the project spec.
    """
    if today is None:
        today = date.today()

    if exam_date <= today:
        raise PlanValidationError("Exam date must be in the future.")

    if daily_hours <= 0:
        raise PlanValidationError("Daily available hours must be greater than zero.")

    study_days = (exam_date - today).days
    total_hours = study_days * float(daily_hours)

    settings = PlanSetting.objects.first()
    revision_percent = float(settings.revision_percent) if settings else 20.0

    revision_hours = total_hours * (revision_percent / 100)
    learning_hours = total_hours - revision_hours

    return {
        'study_days': study_days,
        'total_hours': round(total_hours, 2),
        'revision_hours': round(revision_hours, 2),
        'learning_hours': round(learning_hours, 2),
        'revision_percent': revision_percent,
    }


def rank_eligible_topics(course, completed_or_scheduled_topic_ids, student_rating):
    """
    Returns eligible topics sorted by priority score (descending),
    with learning_order as the tie-breaker (ascending — lower order = earlier).
    """
    eligible = get_eligible_topics(course, completed_or_scheduled_topic_ids)

    scored = []
    for t in eligible:
        priority = calculate_priority_score(t, student_rating)
        scored.append((priority, t.learning_order, t))

    scored.sort(key=lambda x: (-x[0], x[1]))

    return [t for (priority, order, t) in scored]