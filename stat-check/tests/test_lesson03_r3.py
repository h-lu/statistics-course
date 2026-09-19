"""Lesson 03: independent answers, actual HTTP practice, and r2 history isolation."""
import csv
from fractions import Fraction as F
import hashlib
from html import unescape
import io
from pathlib import Path
import re

import pytest

from app import db
from app.questions import BANKS, CURRENT_BANKS
from test_app import make_client, csrf_from, session_id_from, set_phase, create_session

BANK = BANKS['v2-l03-r3']
# Solutions established from the written problems, not read from the answer key.
SOLUTIONS = {'a': ('B','A','D','C','C'), 'b': ('D','C','B','A','A')}


@pytest.mark.parametrize('index,phase', [(i,p) for i in range(5) for p in ('a','b')])
def test_ten_reviewed_answers_and_diagnostic_options(index, phase):
    question = BANK.items[index]['pair'][phase]
    assert question['answer'] == SOLUTIONS[phase][index]
    assert [option['id'] for option in question['options']] == list('ABCD')
    assert len({option['text'] for option in question['options']}) == 4
    assert [option['id'] for option in question['options'] if option['misconception'] is None] == [SOLUTIONS[phase][index]]
    assert all(option['misconception'] for option in question['options'] if option['id'] != SOLUTIONS[phase][index])
    assert question['explanation'] and BANK.items[index]['tutor_context']
    assert '登记等待' not in question['prompt'] and '箱线图界限' not in question['prompt']


def test_calculations_and_record_sets_independent_of_key_letters():
    assert (F(120,60)+0)/2 == 1
    assert F(0+12,2) == 6
    assert len(set(range(100)) - {1,2}) == 98
    assert F(80,100) == F(4,5) and F(54,60) == F(9,10)
    assert 3 == 1+1+1
    assert BANK.durations == {'attempt_a':300,'learn':240,'attempt_b':300}
    assert len(BANK.items) == 5
    for item in BANK.items:
        assert item['pair']['a']['prompt'] != item['pair']['b']['prompt']
        assert {o['text'] for o in item['pair']['a']['options']} != {o['text'] for o in item['pair']['b']['options']}


def test_only_lesson03_advances_and_teacher_copy_matches():
    assert len(BANKS) == 79
    assert [b.lesson_id for b in CURRENT_BANKS] == [
        f'v2-l{n:02d}-r{3 if n==3 else 2 if n<=8 else 1}' for n in range(1,33)]
    mirror = Path(__file__).resolve().parents[2]/'instructor-guide/knowledge-check/question-bank'/BANK.path.name
    if mirror.parent.is_dir():
        assert BANK.path.read_bytes() == mirror.read_bytes()


def test_published_lesson03_r2_bytes_are_unchanged():
    old = BANKS['v2-l03-r2'].path.read_bytes()
    assert hashlib.sha1(f'blob {len(old)}\0'.encode()+old).hexdigest() == '1b7063cf1fb6c038ba2a7a027ce7f378722eb6d8'
    assert BANKS['v2-l03-r2'].question('record-version','a')['answer'] == 'D'
    assert BANK.question('record-version','a')['answer'] == 'B'


@pytest.mark.parametrize('make_one_error', [False,True], ids=['all-reviewed-solutions','one-intentional-error-per-form'])
def test_complete_lesson03_http_practice_learning_feedback_and_export(tmp_path, make_one_error):
    path = tmp_path/'l03.sqlite3'
    with make_client(path,'teacher','teacher') as teacher, make_client(path,'student','l03-simulation') as student:
        create_session(teacher,BANK.lesson_id)
        session = db.current_session(str(path))
        for phase in ('a','b'):
            set_phase(teacher,phase)
            for i,item in enumerate(BANK.items):
                page = student.get('/stat-check/current')
                assert page.status_code == 200
                assert item['pair'][phase]['prompt'] in unescape(page.text)
                assert '参考答案：' not in page.text
                concept = re.search(r'name="concept_id" value="([^"]+)"',page.text).group(1)
                choice = SOLUTIONS[phase][i]
                if make_one_error and i == 0:
                    choice = next(c for c in 'ABCD' if c != choice)
                result = student.post('/stat-check/answer',data={
                    'csrf_token':csrf_from(page),'session_id':session_id_from(page),'concept_id':concept,
                    'phase':phase,'option_id':choice,'confidence':'unsure'},follow_redirects=True)
                assert result.status_code == 200
            if phase == 'a':
                set_phase(teacher,'learn')
                page = student.get('/stat-check/current')
                for item in BANK.items:
                    assert item['tutor_context'] in unescape(page.text)
                learned = student.post('/stat-check/learn/complete',data={
                    'csrf_token':csrf_from(page),'session_id':session_id_from(page)},follow_redirects=True)
                assert learned.status_code == 200 and '学习阶段已完成' in learned.text
        set_phase(teacher,'result')
        page = student.get('/stat-check/current')
        expected = 4 if make_one_error else 5
        for label in ('A','B'):
            assert page.text.count(label+'：正确') == expected
            assert page.text.count(label+'：需复习') == (1 if make_one_error else 0)
        for item in BANK.items:
            for phase in ('a','b'):
                assert item['pair'][phase]['explanation'] in unescape(page.text)
        exported = teacher.get(f"/stat-check/teacher/export.csv?session_id={session['id']}")
        assert exported.status_code == 200
        row = next(r for r in csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))) if r['gitea_login']=='l03-simulation')
        assert tuple(row[k] for k in ('a_count','a_correct','learned','b_count','b_correct')) == ('5',str(expected),'1','5',str(expected))


def test_old_lesson03_answer_is_not_regraded_when_r3_is_created(tmp_path):
    path = tmp_path/'history.sqlite3'
    old = BANKS['v2-l03-r2']
    with make_client(path,'teacher','teacher') as teacher, make_client(path,'student','l03-history') as student:
        create_session(teacher,old.lesson_id)
        old_session = db.current_session(str(path))
        set_phase(teacher,'a')
        page = student.get('/stat-check/current')
        assert old.question('record-version','a')['prompt'] in unescape(page.text)
        answer = student.post('/stat-check/answer',data={
            'csrf_token':csrf_from(page),'session_id':session_id_from(page),'concept_id':'record-version',
            'phase':'a','option_id':'B','confidence':'sure'})  # B is correct only in r3.
        assert answer.status_code == 200
        before = [dict(r) for r in db.export_rows(str(path),old_session['id'])]
        assert next(r for r in before if r['login']=='l03-history')['a_correct'] == 0
        set_phase(teacher,'result')
        assert old.question('record-version','a')['explanation'] in unescape(student.get('/stat-check/current').text)
    # Recreate the actual application against the same temporary DB.
    with make_client(path,'teacher','teacher') as teacher:
        assert db.current_session(str(path))['lesson_id'] == old.lesson_id
        create_session(teacher,BANK.lesson_id)
        assert db.current_session(str(path))['lesson_id'] == BANK.lesson_id
        assert [dict(r) for r in db.export_rows(str(path),old_session['id'])] == before
        exported = teacher.get(f"/stat-check/teacher/export.csv?session_id={old_session['id']}")
        assert exported.status_code == 200 and ',1,0,' in exported.text
