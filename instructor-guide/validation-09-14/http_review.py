"""Local-only HTTP review; synthetic temporary DB, no listener or external account.

Normal TestClient stalls in this executor's cross-thread event-loop wakeup.
A test-only periodic timer bounds selector sleeps; it does not change routes,
answers, application code, installed dependencies or production configuration.
Run from repository root: python3 instructor-guide/validation-09-14/http_review.py
Add --suite to also run the unchanged existing stat-check pytest suite.
"""
from pathlib import Path
import os
import sys
import tempfile
import asyncio
import json
import time
import re
import io
import csv
from html import unescape

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'stat-check'))


def loop_with_test_timer():
    loop=asyncio.new_event_loop()
    def tick():
        if not loop.is_closed(): loop.call_later(.01,tick)
    loop.call_later(.01,tick)
    return loop


def field(response,name):
    match=re.search(r'name="'+name+r'" value="([^"]+)"',response.text)
    assert match, (name,response.status_code,response.text[:200])
    return match.group(1)


def run(folder):
    # All test identities and files are created beneath a temporary directory.
    os.environ.update(SESSION_SECRET='local-review-synthetic-secret',SECURE_COOKIE='false',
                      DATABASE_PATH=str(folder/'import.sqlite3'),TESTING='true')
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.config import Settings
    from app.questions import QuestionBank, BANKS, CURRENT_BANKS
    from app import db
    before_ids=set(BANKS)
    before_current=[b.lesson_id for b in CURRENT_BANKS]
    result=[]
    for n in range(9,15):
        draft=ROOT/f'instructor-guide/knowledge-check/drafts/lessons-09-14-2026-10-11/lesson-v2r2-{n:02}.yml'
        bank=QuestionBank(draft)
        assert bank.lesson_id not in BANKS
        BANKS[bank.lesson_id]=bank  # Only this test process, removed in finally.
        path=folder/f'lesson-{n:02}.sqlite3'
        settings=Settings(database_path=str(path),session_secret='local-review-only',
                          gitea_base_url='https://unused.invalid',gitea_client_id='',gitea_client_secret='',
                          public_base_url='http://testserver/stat-check',teacher_logins=frozenset({'review-teacher'}),
                          testing=True,secure_cookie=False)
        app=create_app(settings)
        kwargs={'backend_options':{'loop_factory':loop_with_test_timer}}
        try:
            with TestClient(app,**kwargs) as teacher,TestClient(app,**kwargs) as student:
                assert teacher.get('/stat-check/healthz').json()=={'status':'ok'}
                assert student.get('/stat-check/teacher').status_code==401
                assert teacher.get('/stat-check/test-login?login=review-teacher&role=teacher').status_code==200
                assert student.get('/stat-check/test-login?login=review-student&role=student').status_code==200
                page=teacher.get('/stat-check/teacher')
                assert f'value="{bank.lesson_id}"' not in page.text
                rejected=teacher.post('/stat-check/teacher/session',data={'csrf_token':field(page,'csrf_token'),'lesson_id':bank.lesson_id})
                assert rejected.status_code==400  # No accidental activation of future sessions.
                db.create_session(str(path),bank.lesson_id,bank.title)  # Test fixture only.
                session=db.current_session(str(path)); sid=session['id']
                for phase in ('a','b'):
                    page=teacher.get('/stat-check/teacher')
                    changed=teacher.post('/stat-check/teacher/phase',data={'csrf_token':field(page,'csrf_token'),'session_id':sid,'phase':phase})
                    assert changed.status_code==200
                    for index,item in enumerate(bank.items):
                        page=student.get('/stat-check/current')
                        assert page.status_code==200
                        concept=field(page,'concept_id')
                        assert concept==item['concept_id']
                        q=bank.question(concept,phase)
                        assert q['prompt'] in unescape(page.text)
                        assert '参考答案：' not in page.text
                        choice=q['answer'] if index else next(c for c in 'ABCD' if c!=q['answer'])
                        response=student.post('/stat-check/answer',data={'csrf_token':field(page,'csrf_token'),
                            'session_id':sid,'concept_id':concept,'phase':phase,'option_id':choice,'confidence':'unsure'})
                        assert response.status_code==200
                    if phase=='a':
                        page=teacher.get('/stat-check/teacher')
                        teacher.post('/stat-check/teacher/phase',data={'csrf_token':field(page,'csrf_token'),'session_id':sid,'phase':'learn'})
                        page=student.get('/stat-check/current')
                        done=student.post('/stat-check/learn/complete',data={'csrf_token':field(page,'csrf_token'),'session_id':sid})
                        assert done.status_code==200 and '学习阶段已完成' in done.text
                page=teacher.get('/stat-check/teacher')
                teacher.post('/stat-check/teacher/phase',data={'csrf_token':field(page,'csrf_token'),'session_id':sid,'phase':'result'})
                feedback=student.get('/stat-check/current')
                assert feedback.status_code==200
                assert feedback.text.count('A：正确')==4 and feedback.text.count('B：正确')==4
                assert feedback.text.count('A：需复习')==1 and feedback.text.count('B：需复习')==1
                for item in bank.items:
                    for q in item['pair'].values():
                        assert q['explanation'] in unescape(feedback.text)
                exported=teacher.get(f'/stat-check/teacher/export.csv?session_id={sid}')
                rows=list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))))
                row=next(r for r in rows if r['gitea_login']=='review-student')
                assert [row[k] for k in ('a_count','a_correct','learned','b_count','b_correct')]==['5','4','1','5','4']
                result.append({'lesson':n,'draft_id':bank.lesson_id,'status':'passed','a_answers':5,'a_correct':4,
                               'learning_complete':True,'b_answers':5,'b_correct':4,
                               'feedback_and_export':'passed','normal_new_session_creation':'still rejected'})
        finally:
            del BANKS[bank.lesson_id]
    assert set(BANKS)==before_ids and [b.lesson_id for b in CURRENT_BANKS]==before_current
    return result


def full_suite(folder):
    # Patch only TestClient construction in this disposable test process.
    from starlette.testclient import TestClient
    original=TestClient.__init__
    def local_init(self,*args,**kwargs):
        options=dict(kwargs.get('backend_options') or {})
        options.setdefault('loop_factory',loop_with_test_timer)
        kwargs['backend_options']=options
        original(self,*args,**kwargs)
    TestClient.__init__=local_init
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
    import pytest
    try:
        return pytest.main(['-q',str(ROOT/'stat-check/tests'),'--basetemp',str(folder/'pytest')])
    finally:
        TestClient.__init__=original


if __name__=='__main__':
    start=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='statistics-http-review-') as temp:
        folder=Path(temp)
        result={'transport':'in-process ASGI HTTP through TestClient; no TCP server',
                'test_only_adjustment':'10ms event-loop timer; no application changes',
                'lessons':run(folder),'existing_suite_exit_code':None}
        if '--suite' in sys.argv: result['existing_suite_exit_code']=int(full_suite(folder))
    result['seconds']=round(time.perf_counter()-start,3)
    (HERE/'http_review_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['existing_suite_exit_code'] not in (None,0): raise SystemExit(1)
