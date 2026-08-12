from datetime import date
from .models import PlanSetting
from .models import Topic, PYQQuestion, PlanSetting
from .models import Topic, TopicDependency
from datetime import timedelta
from .models import PlanSetting, Topic, PYQQuestion, TopicDependency, StudySession, UserCourseRating

def generate_schedule(course, student_rating, exam_date, daily_hours, start_date=None):
    """
    Generates a day-by-day list of sessions for ALL topics in the course,
    respecting prerequisites, priority order, session splitting, daily
    capacity, and basic course-fairness (max 2 consecutive same-course
    blocks isn't needed yet since this handles ONE course at a time --
    multi-course fairness comes when you extend this to multiple courses).
    """
    if start_date is None:
        start_date = date.today()

    all_topics = list(Topic.objects.filter(course=course))
    completed_ids = []
    # Each entry: {topic, remaining_hours}
    remaining_work = {t.id: float(t.estimated_hours) for t in all_topics}

    schedule = []  # list of dicts: {date, topic, duration}
    current_date = start_date
    days_scheduled = 0
    max_days = (exam_date - start_date).days

    while remaining_work and days_scheduled < max_days:
        day_capacity = float(daily_hours)
        day_sessions = []

        while day_capacity > 0:
            ranked = rank_eligible_topics(course, completed_ids, student_rating)
            # Only consider topics that still have remaining hours
            ranked = [t for t in ranked if remaining_work.get(t.id, 0) > 0]

            if not ranked:
                break  # nothing eligible/left to schedule today

            topic = ranked[0]
            block = min(MAX_BLOCK_HOURS, remaining_work[topic.id], day_capacity)
            block = round(block, 2)

            day_sessions.append({'date': current_date, 'topic': topic, 'duration': block})
            remaining_work[topic.id] -= block
            day_capacity -= block

            if remaining_work[topic.id] <= 0:
                del remaining_work[topic.id]
                completed_ids.append(topic.id)  # treat as "scheduled" so dependents unlock

        schedule.extend(day_sessions)
        current_date += timedelta(days=1)
        days_scheduled += 1

    return schedule

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

MAX_BLOCK_HOURS = 2.0  # configurable max session length


def split_into_blocks(estimated_hours, max_block_hours=MAX_BLOCK_HOURS):
    """
    Splits a topic's total hours into a list of session block sizes.
    E.g. 4.5 hours with max 2.0 -> [2.0, 2.0, 0.5]
    """
    blocks = []
    remaining = float(estimated_hours)
    while remaining > 0:
        block = min(max_block_hours, remaining)
        blocks.append(round(block, 2))
        remaining -= block
    return blocks

from datetime import date as date_cls


def mark_overdue_sessions_as_missed(plan):
    """
    Any 'pending' session whose date has already passed becomes 'missed'.
    Matches Section 14.2: status changes automatically once the date passes.
    """
    from .models import StudySession
    overdue = StudySession.objects.filter(
        plan=plan, status='pending', date__lt=date_cls.today()
    )
    count = overdue.update(status='missed')
    return count

def regenerate_plan(plan):
    """
    Reallocates missed and pending-future work across remaining days.
    Completed sessions are never touched. Returns a dict summary.
    """
    today = date_cls.today()

    # Step 1: find missed sessions (unfinished work to reschedule)
    missed_sessions = StudySession.objects.filter(plan=plan, status='missed')

    if not missed_sessions.exists():
        return {'rescheduled_count': 0, 'shortage_hours': 0}

    # Step 3: remaining days between today and exam
    remaining_days = (plan.exam_date - today).days
    if remaining_days <= 0:
        return {'rescheduled_count': 0, 'shortage_hours': sum(float(s.duration) for s in missed_sessions), 'error': 'No days remaining before exam.'}

    # Step 4: group missed hours back by topic (Step 4 of spec: "return unfinished blocks to queue")
    from collections import defaultdict
    unfinished_by_topic = defaultdict(float)
    for s in missed_sessions:
        unfinished_by_topic[s.topic_id] += float(s.duration)

    # Step 6: find existing future capacity already used, to know what's free per day
    future_sessions = StudySession.objects.filter(
        plan=plan, date__gte=today
    ).exclude(status='completed')
    daily_used = defaultdict(float)
    for s in future_sessions:
        daily_used[s.date] += float(s.duration)

    daily_capacity = float(plan.daily_hours)

    # Step 5: prioritize which topic's missed hours go first
    from .models import Topic
    topics_by_priority = []
    for topic_id, hours in unfinished_by_topic.items():
        topic = Topic.objects.get(id=topic_id)
        rating_obj = UserCourseRating.objects.filter(user=plan.user, course=topic.course).first()
        rating = rating_obj.rating if rating_obj else 5
        priority = calculate_priority_score(topic, rating)
        topics_by_priority.append((priority, topic, hours))
    topics_by_priority.sort(key=lambda x: -x[0])

    # Delete the old missed session rows -- they're being replaced by new ones
    missed_sessions.delete()

    rescheduled_count = 0
    shortage_hours = 0

    for priority, topic, hours_needed in topics_by_priority:
        remaining_to_place = hours_needed
        check_date = today

        while remaining_to_place > 0 and check_date <= plan.exam_date:
            used = daily_used[check_date]
            free = daily_capacity - used

            if free > 0:
                block = min(MAX_BLOCK_HOURS, remaining_to_place, free)
                block = round(block, 2)
                StudySession.objects.create(
                    plan=plan, topic=topic, date=check_date,
                    duration=block, session_type='learning',
                    status='rescheduled'
                )
                daily_used[check_date] += block
                remaining_to_place -= block
                rescheduled_count += 1

            check_date += timedelta(days=1)

        if remaining_to_place > 0:
            # Step 9: couldn't fit everything before the exam
            shortage_hours += remaining_to_place

    return {'rescheduled_count': rescheduled_count, 'shortage_hours': round(shortage_hours, 2)}

def generate_revision_sessions(course, topics_studied, exam_date, revision_hours_available, student_rating):
    """
    Places revision blocks in the final portion of the plan, highest-priority
    topics first. Revision NEVER lands on the exam date itself — the day
    before the exam is reserved as a dedicated final review of the most
    important topics only.
    """
    if revision_hours_available <= 0 or not topics_studied:
        return []

    scored = []
    for topic in topics_studied:
        priority = calculate_priority_score(topic, student_rating)
        scored.append((priority, topic))
    scored.sort(key=lambda x: -x[0])

    today = date_cls.today()
    # Last usable revision day is exam_date - 1, never the exam date itself
    last_revision_day = exam_date - timedelta(days=1)

    total_days = (last_revision_day - today).days
    revision_window_days = max(1, round(total_days * 0.3))
    revision_start = last_revision_day - timedelta(days=revision_window_days)

    sessions = []
    remaining_hours = revision_hours_available
    current_date = max(revision_start, today)
    day_used = 0.0
    max_daily_revision = 1.5

    # Reserve the top 3 highest-priority topics for a dedicated final review
    # session the day before the exam, separate from the regular rotation.
    final_review_topics = [t for (p, t) in scored[:3]]
    final_review_hours_each = 1.0

    for priority, topic in scored:
        if remaining_hours <= 0:
            break
        # Skip ahead of the final-review day during the normal rotation --
        # that day is reserved separately, below.
        if current_date >= last_revision_day:
            break

        block = min(max_daily_revision, remaining_hours)
        block = round(block, 2)

        sessions.append({'date': current_date, 'topic': topic, 'duration': block})
        remaining_hours -= block
        day_used += block

        if day_used >= max_daily_revision:
            current_date += timedelta(days=1)
            day_used = 0.0

    # Dedicated final review, always the day before the exam
    if last_revision_day >= today:
        for topic in final_review_topics:
            sessions.append({
                'date': last_revision_day,
                'topic': topic,
                'duration': final_review_hours_each,
            })

    return sessions

def check_capacity(total_hours_required, total_hours_available):
    """
    Returns (fits, shortage_hours). Section 14.3: 'the system should not
    silently create impossible schedules.'
    """
    if total_hours_required <= total_hours_available:
        return True, 0
    shortage = round(total_hours_required - total_hours_available, 2)
    return False, shortage