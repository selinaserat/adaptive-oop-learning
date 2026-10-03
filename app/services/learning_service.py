from app.repositories.base import Repository

class APIError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details

class LearningService:
    def __init__(self, repository: Repository, threshold=80):
        self.repo, self.threshold = repository, threshold
        self._validate_curriculum()

    def _validate_curriculum(self):
        topics = {t['topic_id']: t for t in self.repo.get_topics()}
        visited, visiting, question_ids = set(), set(), set()
        def visit(i):
            if i in visiting: raise ValueError('Curriculum contains a prerequisite cycle')
            if i in visited: return
            if i not in topics: raise ValueError('Unknown prerequisite topic')
            visiting.add(i)
            for p in topics[i]['prerequisites']: visit(p)
            visiting.remove(i)
            visited.add(i)
        for i in topics:
            visit(i)
            questions = self.repo.get_questions(i)
            if not questions: raise ValueError('Each topic needs quiz questions')
            for q in questions:
                if q['question_id'] in question_ids or q['answer'] not in q['options']:
                    raise ValueError('Invalid or duplicate question')
                question_ids.add(q['question_id'])

    def student(self, student_id):
        student = self.repo.get_student(student_id)
        if student is None: raise APIError(404, 'student_not_found', 'Student not found')
        return student

    def topic(self, topic_id):
        topic = self.repo.get_topic(topic_id)
        if topic is None: raise APIError(404, 'topic_not_found', 'Topic not found')
        return {k:topic[k] for k in ('topic_id','title','description','prerequisites','lesson')}

    def topics(self):
        return {'topics':[self.topic(t['topic_id']) for t in self.repo.get_topics()]}

    @staticmethod
    def public_question(q):
        result = {k:q[k] for k in ('question_id','question','options')}
        if 'topic_id' in q: result['topic_id'] = q['topic_id']
        return result

    def quiz(self, topic_id):
        topic = self.topic(topic_id)
        return dict(topic_id=topic_id, topic_title=topic['title'],
                    questions=[self.public_question(q) for q in self.repo.get_questions(topic_id)])

    def diagnostic(self):
        return {'questions':[self.public_question(q) for q in self.repo.get_diagnostic_questions()]}

    def create_student(self, payload):
        if not isinstance(payload, dict) or set(payload) != {'name'}:
            raise APIError(400,'invalid_request','Provide only a name field')
        name = payload['name']
        if not isinstance(name,str) or not 1 <= len(name.strip()) <= 100:
            raise APIError(400,'invalid_name','Name must contain 1–100 characters')
        return {'student':self.repo.create_student(name.strip())}

    def _progress(self, student_id):
        records = self.repo.get_progress(student_id)
        mastered = {p.topic_id for p in records if p.state == 'mastered'}
        return [dict(p.to_dict(), unlocked=all(i in mastered for i in self.topic(p.topic_id)['prerequisites']))
                for p in records]

    def _recommendation(self, student_id, progress):
        if not self.student(student_id)['diagnostic_completed']:
            return dict(action='take_diagnostic',topic_id=None,reason='Complete the diagnostic first')
        eligible = sorted((p for p in progress if p['unlocked'] and p['state'] != 'mastered'),
                          key=lambda p:(p['state'] != 'in_progress', p['topic_id']))
        if eligible:
            p=eligible[0]
            return dict(action='review' if p['state']=='in_progress' else 'start_topic',
                        topic_id=p['topic_id'],reason='Review and retry' if p['state']=='in_progress' else 'Prerequisites are mastered')
        return dict(action='completed',topic_id=None,reason='All topics are mastered')

    def dashboard(self, student_id):
        with self.repo.transaction(student_id):
            student = self.student(student_id)
            progress = self._progress(student_id)
            return dict(student=student, mastery_threshold=self.threshold, progress=progress,
                        recommendation=self._recommendation(student_id,progress))

    def progress(self, student_id):
        d=self.dashboard(student_id)
        return {k:d[k] for k in ('mastery_threshold','progress','recommendation')}

    def attempts(self, student_id):
        with self.repo.transaction(student_id):
            self.student(student_id)
            return {'attempts':self.repo.get_attempts_for_student(student_id)}

    @staticmethod
    def validate_answers(payload, questions):
        if not isinstance(payload,dict) or set(payload) != {'answers'} or not isinstance(payload['answers'],dict):
            raise APIError(400,'invalid_request','Provide only an answers object')
        answers=payload['answers']
        expected={str(q['question_id']) for q in questions}
        if set(answers) != expected:
            raise APIError(400,'invalid_answers','Submit exactly one answer for every assessment question',
                           dict(missing=sorted(expected-set(answers)),unknown=sorted(set(answers)-expected)))
        for q in questions:
            answer=answers[str(q['question_id'])]
            if not isinstance(answer,str) or answer not in q['options']:
                raise APIError(400,'invalid_option','Answers must be valid option labels')
        return answers

    @staticmethod
    def score(questions, answers):
        correct=sum(answers[str(q['question_id'])] == q['answer'] for q in questions)
        return dict(correct_count=correct,question_count=len(questions),score=round(100*correct/len(questions),2))

    def _update(self, student_id, topic_id, result):
        p=next(p for p in self.repo.get_progress(student_id) if p.topic_id==topic_id)
        p.latest_score=result['score']
        p.best_score=max(p.best_score or 0,result['score'])
        # Compare the fraction itself: rounding must never turn <80% into mastery.
        passed=result['correct_count']*100 >= self.threshold*result['question_count']
        if passed: p.state='mastered'
        elif p.state != 'mastered': p.state='in_progress'
        self.repo.update_progress(student_id,p)
        return p.state

    def submit(self, student_id, payload, topic_id=None):
        with self.repo.transaction(student_id):
            student=self.student(student_id)
            if topic_id is not None:
                topic=self.topic(topic_id)
                if not student['diagnostic_completed']:
                    raise APIError(403,'diagnostic_required','Complete the diagnostic before topic quizzes')
                mastered={p.topic_id for p in self.repo.get_progress(student_id) if p.state=='mastered'}
                missing=[p for p in topic['prerequisites'] if p not in mastered]
                if missing: raise APIError(403,'prerequisites_not_met','Master prerequisite topics first',{'missing_topic_ids':missing})
                questions=self.repo.get_questions(topic_id)
            else:
                questions=self.repo.get_diagnostic_questions()
            answers=self.validate_answers(payload,questions)
            result=self.score(questions,answers)
            topic_results=[]
            for i in sorted({q['topic_id'] for q in questions} if topic_id is None else {topic_id}):
                subset=[q for q in questions if q.get('topic_id',topic_id)==i]
                scored=self.score(subset,answers)
                state=self._update(student_id,i,scored)
                topic_results.append(dict(topic_id=i,state=state,**scored))
            if topic_id is None: self.repo.mark_diagnostic_completed(student_id)
            attempt=self.repo.add_attempt(student_id,dict(kind='diagnostic' if topic_id is None else 'quiz',
                topic_id=topic_id, **result, topic_results=topic_results))
            return dict(attempt=attempt,**self.progress(student_id))
