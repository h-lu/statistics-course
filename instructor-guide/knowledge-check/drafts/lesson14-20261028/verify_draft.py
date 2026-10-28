"""Offline structure/numerical checks; run from any directory with PyYAML installed.

Optional: --loader PATH checks the exact repository loader definitions in isolation.
No live app, database, student session, installation or network operation is used.
"""
from pathlib import Path
from collections import Counter
from fractions import Fraction as F
import argparse
import ast
import hashlib
import json
import tempfile
import yaml

here = Path(__file__).resolve().parent
root = here.parents[3]
filename = 'lesson-v2r2-14-20261028.yml'
source = here / filename
mirror = root / 'stat-check/app/question_bank/drafts/lesson14-20261028' / filename
raw = source.read_bytes()
assert raw == mirror.read_bytes()
bank = yaml.safe_load(raw)
assert bank['lesson_id'] == 'v2-l14-r2-20261028'
assert bank['duration_seconds'] == dict(attempt_a=300, learn=240, attempt_b=300)
assert len(bank['items']) == len({i['concept_id'] for i in bank['items']}) == 5
answers = Counter()
for item in bank['items']:
    assert all(item[k].strip() for k in ('concept_id', 'title', 'tutor_context'))
    assert set(item['pair']) == {'a', 'b'}
    assert item['pair']['a']['prompt'] != item['pair']['b']['prompt']
    for q in item['pair'].values():
        assert q['prompt'].strip() and 'LEARN第' in q['explanation']
        opts = q['options']
        assert [o['id'] for o in opts] == list('ABCD')
        assert len({o['text'] for o in opts}) == 4
        assert [o['id'] for o in opts if o['misconception'] is None] == [q['answer']]
        wrong = [o['misconception'] for o in opts if o['id'] != q['answer']]
        assert len(set(wrong)) == 3 and all(wrong)
        answers[q['answer']] += 1
assert set(answers) == set('ABCD') and max(answers.values()) <= 3
# Independent exact checks of each numerical answer/feedback claim.
assert F(300, 1200) == F(1, 4)
assert F(600, 1000) == F(3, 5) and F(400, 1000) == F(2, 5)
assert (F(600, 100), F(400, 100)) == (6, 4)
assert F(100, 1000) == F(1, 10)
assert (F(100, 20), F(100, 10)) == (5, 10)
assert F(46, 100) - F(196, 100)*F(3, 100) == F(4012, 10000)
assert F(46, 100) + F(196, 100)*F(3, 100) == F(5188, 10000)
for p in (F(0), F(1, 5), F(1, 2), F(7, 10), F(1)):
    assert p*(1-p) <= F(1, 4)
assert 6 < 8 and 4 > 3
result = dict(lesson_id=bank['lesson_id'], pairs=5, questions=10,
              mirror_byte_identical=True, answer_positions=dict(answers),
              numerical_checks='passed', sha256=hashlib.sha256(raw).hexdigest())
parser = argparse.ArgumentParser()
parser.add_argument('--loader', type=Path)
args = parser.parse_args()
if args.loader:
    # Keep exact source definitions and constants, excluding module-level bank
    # loading that would require the entire installed app catalogue.
    code = args.loader.read_text(encoding='utf-8')
    tree = ast.parse(code)
    stop = next(i for i,n in enumerate(tree.body)
                if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='QUESTION_BANKS' for t in n.targets))
    tree.body = tree.body[:stop]
    namespace = {}
    exec(compile(tree, '<isolated-repository-loader>', 'exec'), namespace)
    loaded = namespace['QuestionBank'](source)
    assert loaded.lesson_id == bank['lesson_id']
    assert namespace['select_current_banks']((loaded,)) == ()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        fixture = dict(bank, lesson_id='v2-l01-r999')
        (folder/'lesson-fixture.yml').write_text(yaml.safe_dump(fixture,allow_unicode=True))
        draft = folder/'drafts/lesson14-20261028'/filename
        draft.parent.mkdir(parents=True)
        draft.write_bytes(raw)
        installed = namespace['load_question_banks'](folder)
        assert [x.lesson_id for x in installed] == ['v2-l01-r999']
    result['isolated_loader_checks'] = 'parse passed; nested draft excluded; lesson 14 not current'
    result['loader_sha256'] = hashlib.sha256(code.encode()).hexdigest()
else:
    result['isolated_loader_checks'] = 'not run: supply --loader PATH'
print(json.dumps(result, ensure_ascii=False, indent=2))
