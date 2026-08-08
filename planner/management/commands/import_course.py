import csv
from django.core.management.base import BaseCommand
from planner.models import Course, Topic, TopicDependency, PYQQuestion


class Command(BaseCommand):
    help = 'Imports a course and its topics, prerequisites, and PYQ questions from CSV files'

    def add_arguments(self, parser):
        parser.add_argument('course_csv', type=str)
        parser.add_argument('topic_csv', type=str)
        parser.add_argument('stats_csv', type=str)
        parser.add_argument('prereq_csv', type=str)
        parser.add_argument('pyq_csv', type=str)

    def handle(self, *args, **options):
        # 1. Course
        with open(options['course_csv'], encoding='utf-8-sig') as f:
            row = next(csv.DictReader(f))
            course, created = Course.objects.get_or_create(
                course_code=row['course_code'].strip(),
                defaults={
                    'course_name': row['course_name'].strip(),
                    'semester': int(row['semester']),
                    'active': row['active'].strip().upper() == 'TRUE',
                }
            )
            self.stdout.write(self.style.SUCCESS(f"Course: {course.course_code} ({'created' if created else 'exists'})"))

        # 2. Load stats (for importance) into a lookup dict
        importance_lookup = {}
        with open(options['stats_csv'], encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                importance_lookup[row['Topic'].strip()] = float(row['Importance'])

        # 3. Topics
        topic_lookup = {}
        with open(options['topic_csv'], encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                name = row['Topic'].strip()
                topic, _ = Topic.objects.get_or_create(
                    course=course, name=name,
                    defaults={
                        'importance': importance_lookup.get(name, 5),
                        'estimated_hours': float(row['Estimated Hours']),
                        'learning_order': int(row['Learning Order']),
                    }
                )
                topic_lookup[name] = topic
        self.stdout.write(self.style.SUCCESS(f"Topics imported: {len(topic_lookup)}"))

        # 4. Prerequisites
        dep_count = 0
        with open(options['prereq_csv'], encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                prereq_name = row['Prerequisite Topic'].strip()
                if prereq_name and prereq_name in topic_lookup:
                    TopicDependency.objects.get_or_create(
                        topic=topic_lookup[row['Topic'].strip()],
                        prerequisite_topic=topic_lookup[prereq_name],
                    )
                    dep_count += 1
        self.stdout.write(self.style.SUCCESS(f"Dependencies imported: {dep_count}"))

        # 5. PYQ Questions
        q_count = 0
        with open(options['pyq_csv'], encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                topic_name = row['Topic'].strip()
                if topic_name in topic_lookup:
                    PYQQuestion.objects.create(
                        course=course,
                        topic=topic_lookup[topic_name],
                        subtopic=row['Subtopic'].strip(),
                        term=row['Term / Paper'].strip(),
                        year=int(row['Term / Paper'].strip()[-4:]),
                        marks=float(row['Marks']),
                        question_text=row['Question'].strip(),
                    )
                    q_count += 1
        self.stdout.write(self.style.SUCCESS(f"Questions imported: {q_count}"))