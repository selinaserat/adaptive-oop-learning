"""Local development only: process-local storage with atomic, rollback-safe writes."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from app.data.mock_data import TOPICS, QUESTIONS
from app.models.domain import Progress

def utc_now():
    return datetime.now(timezone.utc).isoformat()

class MemoryRepository:
    persistent = False

    def __init__(self, topics=None, questions=None):
        self.topics = deepcopy(TOPICS if topics is None else topics)
        self.questions = deepcopy(QUESTIONS if questions is None else questions)
        self.students, self.progress, self.attempts = {}, {}, []
        self.lock = RLock()

    @contextmanager
    def transaction(self, student_id=None):
        with self.lock:
            snapshot = deepcopy((self.students, self.progress, self.attempts))
            try:
                yield
            except Exception:
                self.students, self.progress, self.attempts = snapshot
                raise

    def get_topics(self):
        return [dict(deepcopy(t), topic_id=i) for i,t in sorted(self.topics.items())]

    def get_topic(self, topic_id):
        t = self.topics.get(topic_id)
        return dict(deepcopy(t), topic_id=topic_id) if t else None

    def get_questions(self, topic_id):
        return deepcopy(self.questions.get(topic_id, []))

    def get_diagnostic_questions(self):
        return [dict(q, topic_id=t['topic_id']) for t in self.get_topics()
                for q in self.get_questions(t['topic_id'])]

    def create_student(self, name):
        with self.transaction():
            student_id = max(self.students, default=0) + 1
            student = dict(student_id=student_id, name=name, created_at=utc_now(), diagnostic_completed=False)
            self.students[student_id] = student
            self.progress[student_id] = {}
            return deepcopy(student)

    def get_student(self, student_id):
        return deepcopy(self.students.get(student_id))

    def mark_diagnostic_completed(self, student_id):
        self.students[student_id]['diagnostic_completed'] = True

    def get_progress(self, student_id):
        return [deepcopy(self.progress[student_id].get(t['topic_id'], Progress(t['topic_id'])))
                for t in self.get_topics()]

    def update_progress(self, student_id, progress):
        self.progress[student_id][progress.topic_id] = deepcopy(progress)

    def add_attempt(self, student_id, attempt):
        record = dict(deepcopy(attempt), attempt_id=len(self.attempts)+1,
                      student_id=student_id, created_at=utc_now())
        self.attempts.append(record)
        return deepcopy(record)

    def get_attempts_for_student(self, student_id):
        return deepcopy([a for a in self.attempts if a['student_id']==student_id])
