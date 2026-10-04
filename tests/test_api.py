import pytest
from app import create_app
from app.repositories.memory_repository import MemoryRepository

CORRECT={'101':'A','102':'B','201':'A','202':'B','301':'A','302':'A'}
WRONG={'101':'D','102':'D','201':'D','202':'D','301':'D','302':'D'}

@pytest.fixture
def client():
    return create_app({'TESTING':True}).test_client()

def student(client):
    return client.post('/api/students',json={'name':'Selina'}).json['student']['student_id']

def diagnose(client,s,answers=WRONG):
    return client.post(f'/api/students/{s}/diagnostic',json={'answers':answers})

def quiz(client,s,t,answers):
    return client.post(f'/api/students/{s}/topics/{t}/quiz',json={'answers':answers})

def assert_no_keys(value):
    if isinstance(value,dict):
        assert not {'answer','answers','correct_answer'} & value.keys()
        for v in value.values(): assert_no_keys(v)
    elif isinstance(value,list):
        for v in value: assert_no_keys(v)

def test_health_topics_lessons(client):
    assert client.get('/api/health').json['status']=='ok'
    assert len(client.get('/api/topics').json['topics'])==3
    assert client.get('/api/topics/1').json['topic']['lesson']['content']

@pytest.mark.parametrize('path',['/api/topics/1/quiz','/api/diagnostic','/api/topics','/api/topics/1'])
def test_no_answer_leaks(client,path):
    r=client.get(path)
    assert r.status_code==200
    assert_no_keys(r.json)

def test_creation_and_dashboard(client):
    r=client.post('/api/students',json={'name':' Selina '})
    assert r.status_code==201
    assert r.json['student']['name']=='Selina'
    d=client.get('/api/students/1/dashboard').json
    assert d['recommendation']['action']=='take_diagnostic'
    assert all(p['state']=='not_started' for p in d['progress'])

def test_mastery_next_topic_and_history(client):
    s=student(client); diagnose(client,s)
    r=quiz(client,s,1,{'101':'A','102':'B'})
    assert r.status_code==200
    assert r.json['attempt']['score']==100
    assert r.json['progress'][0]['state']=='mastered'
    assert r.json['recommendation']['topic_id']==2
    assert r.json['progress'][1]['unlocked']
    assert not r.json['progress'][2]['unlocked']
    assert len(client.get(f'/api/students/{s}/attempts').json['attempts'])==2
    assert_no_keys(r.json)
    assert_no_keys(client.get(f'/api/students/{s}/attempts').json)

def test_low_score_and_blocking(client):
    s=student(client)
    assert quiz(client,s,1,{'101':'A','102':'B'}).json['error']['code']=='diagnostic_required'
    diagnose(client,s)
    r=quiz(client,s,1,{'101':'A','102':'D'})
    assert r.json['attempt']['score']==50
    assert r.json['progress'][0]['state']=='in_progress'
    assert r.json['recommendation']=={'action':'review','topic_id':1,'reason':'Review and retry'}
    assert quiz(client,s,2,{'201':'A','202':'B'}).status_code==403
    assert len(client.get(f'/api/students/{s}/attempts').json['attempts'])==2

def test_diagnostic_topic_performance(client):
    s=student(client)
    r=diagnose(client,s,dict(WRONG,**{'101':'A','102':'B'}))
    assert r.json['attempt']['score']==33.33
    assert r.json['attempt']['topic_results'][0]['score']==100
    assert r.json['recommendation']['topic_id']==2
    assert client.get(f'/api/students/{s}/dashboard').json['student']['diagnostic_completed']

def test_completion_and_monotonic_mastery(client):
    s=student(client)
    assert diagnose(client,s,CORRECT).json['recommendation']['action']=='completed'
    r=quiz(client,s,1,{'101':'D','102':'D'})
    assert r.json['progress'][0]['state']=='mastered'
    assert r.json['progress'][0]['best_score']==100
    assert r.json['progress'][0]['latest_score']==0
    assert diagnose(client,s,WRONG).json['recommendation']['action']=='completed'

def test_exact_80_percent():
    repo=MemoryRepository(topics={1:dict(title='Test',description='Test',prerequisites=[],lesson={})},
        questions={1:[dict(question_id=i,question='Q',options={'A':'yes','B':'no'},answer='A') for i in range(1,6)]})
    client=create_app({'TESTING':True},repository=repo).test_client()
    s=student(client)
    r=diagnose(client,s,{str(i):'A' if i<5 else 'B' for i in range(1,6)})
    assert r.json['attempt']['score']==80
    assert r.json['progress'][0]['state']=='mastered'

@pytest.mark.parametrize('payload',[None,[],{}, {'name':''},{'name':9},{'name':'x'*101},{'name':'a','score':100}])
def test_invalid_student(client,payload):
    assert client.post('/api/students',json=payload).status_code in (400,415)

@pytest.mark.parametrize('answers',[{}, {'101':'A'},{**CORRECT,'999':'A'},{**CORRECT,'101':'Z'},{**CORRECT,'101':[]},{**CORRECT,'101':'a'}])
def test_invalid_answers_no_writes(client,answers):
    s=student(client)
    assert diagnose(client,s,answers).status_code==400
    assert client.get(f'/api/students/{s}/attempts').json=={'attempts':[]}
    assert client.get(f'/api/students/{s}/dashboard').json['student']['diagnostic_completed'] is False

@pytest.mark.parametrize('path',['/api/nope','/api/topics/999','/api/topics/999/quiz','/api/students/999/dashboard','/api/students/999/progress','/api/students/999/attempts'])
def test_404(client,path):
    r=client.get(path)
    assert r.status_code==404 and 'error' in r.json

def test_submission_missing_entities(client):
    assert diagnose(client,999).status_code==404
    s=student(client)
    assert quiz(client,s,999,{}).status_code==404

def test_transport_errors_and_cors(client):
    assert client.post('/api/students',data='{',content_type='application/json').status_code==400
    assert client.put('/api/health').status_code==405
    assert client.post('/api/students',data='x'*70000,content_type='application/json').status_code==413
    allowed=client.get('/api/health',headers={'Origin':'http://localhost:3000'})
    assert allowed.headers['Access-Control-Allow-Origin']=='http://localhost:3000'
    denied=client.get('/api/health',headers={'Origin':'https://untrusted.example'})
    assert 'Access-Control-Allow-Origin' not in denied.headers
    preflight=client.options('/api/students',headers={'Origin':'http://localhost:3000','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type'})
    assert preflight.status_code==200
    assert 'POST' in preflight.headers['Access-Control-Allow-Methods']

def test_rollback_and_safe_500(client,monkeypatch):
    s=student(client)
    repo=client.application.extensions['repository']
    def fail(*args): raise RuntimeError('private database secret')
    monkeypatch.setattr(repo,'add_attempt',fail)
    r=diagnose(client,s,CORRECT)
    assert r.status_code==500
    assert 'secret' not in str(r.json)
    d=client.get(f'/api/students/{s}/dashboard').json
    assert not d['student']['diagnostic_completed']
    assert all(p['state']=='not_started' for p in d['progress'])

def test_production_guard():
    with pytest.raises(RuntimeError): create_app({'APP_ENV':'production'})

def test_repository_isolation():
    a,b=MemoryRepository(),MemoryRepository()
    a.create_student('A')
    assert b.get_student(1) is None
    topics=a.get_topics();topics[0]['title']='changed'
    assert a.get_topic(1)['title']=='Classes and Objects'

def test_students_do_not_share_progress(client):
    first, second=student(client),student(client)
    diagnose(client,first,CORRECT)
    d=client.get(f'/api/students/{second}/dashboard').json
    assert not d['student']['diagnostic_completed']
    assert all(p['state']=='not_started' for p in d['progress'])
    assert client.get(f'/api/students/{second}/attempts').json['attempts']==[]


def test_concurrent_submissions_preserve_attempts():
    from concurrent.futures import ThreadPoolExecutor
    app=create_app({'TESTING':True})
    service=app.extensions['learning_service']
    s=service.create_student({'name':'Concurrent'})['student']['student_id']
    service.submit(s,{'answers':WRONG})
    def submit(_):
        return service.submit(s,{'answers':{'101':'A','102':'B'}},1)['attempt']['attempt_id']
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids=list(pool.map(submit,range(8)))
    assert len(set(ids))==8
    assert len(service.attempts(s)['attempts'])==9
    assert service.progress(s)['progress'][0]['state']=='mastered'


def test_new_topic_requires_no_route_changes():
    repo=MemoryRepository()
    repo.topics[4]=dict(title='Inheritance',description='Reuse',prerequisites=[3],
                        lesson={'format':'plain_text','content':'Inheritance'})
    repo.questions[4]=[dict(question_id=401,question='Q',options={'A':'yes','B':'no'},answer='A')]
    client=create_app({'TESTING':True},repository=repo).test_client()
    s=student(client)
    answers=dict(CORRECT,**{'401':'B'})
    r=diagnose(client,s,answers)
    assert r.json['recommendation']['topic_id']==4
    assert quiz(client,s,4,{'401':'A'}).json['recommendation']['action']=='completed'


def test_curriculum_cycle_rejected():
    repo=MemoryRepository()
    repo.topics[1]['prerequisites']=[3]
    with pytest.raises(ValueError,match='cycle'):
        create_app({'TESTING':True},repository=repo)


def test_explicit_preview_mode():
    client=create_app({'APP_ENV':'preview','TESTING':True}).test_client()
    page=client.get('/')
    assert page.status_code==200
    assert b'Project preview' in page.data
    assert b'Use test names only' in page.data
    s=student(client)
    assert diagnose(client,s,CORRECT).status_code==200


def test_unknown_environment_rejected():
    with pytest.raises(ValueError,match='APP_ENV'):
        create_app({'APP_ENV':'prodution'})
