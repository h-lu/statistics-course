"""Lesson 03 reading, worked-project and data contracts; no live student writes."""
import csv
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
STUDENT = ROOT / 'student-template'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REF = load(Path(__file__).with_name('reference.py'), 'lesson03_reference')
WALK = load(Path(__file__).with_name('walkthrough.py'), 'lesson03_walkthrough')


def test_learning_example_only_checks_the_declared_fields():
    text = (STUDENT / 'lesson-03/LEARN.md').read_text(encoding='utf-8')
    blocks = re.findall(r'```python\n(.*?)```', text, re.S)
    code = next(block for block in blocks if '# learning-example' in block)
    # An unrelated blank note must not change the analysis's required fields.
    code = code.replace('waits = ', 'for row in rows:\n    row["unrelated_note"] = None\nwaits = ', 1)
    env = {}
    exec(compile(code, '<lesson03-learning-example>', 'exec'), env)
    assert env['result'] == {'target_n': 3, 'wait_n': 2, 'wait_mean': 31.5,
                             'completion_rate': 2/3, 'complete_case_rate': 1/2, 'known_window_n': 2}


def test_extra_reading_questions_do_not_count_issues_as_people():
    missing_wait, unknown_window = {'T1', 'T2', 'T3'}, {'T3', 'T4'}
    assert len(missing_wait | unknown_window) == 4
    assert REF.u.rate(0, 0) is None
    rows = [{'ticket_id': 'T1', 'wait': 12, 'abandon': None, 'completed': 1,
             'center': 'A', 'window_id': 'A1', 'quality_flags': ['missing_abandonment']}]
    assert REF.build_result(rows, {})['served_valid_wait']['n'] == 0


@pytest.mark.parametrize('value,expected,flag', [
    ('0', 0, None), ('1', 1, None), (0, 0, None),
    ('', None, 'missing_completion'), ('  ', None, 'missing_completion'),
    (None, None, 'missing_completion'), ('2', None, 'invalid_completion'),
    ('text', None, 'invalid_completion'),
])
def test_invalid_and_missing_binary_values_are_distinct(value, expected, flag):
    assert REF.parse_binary(value, 'completion') == (expected, flag)


def test_declared_three_and_five_information_sets_are_not_conflated():
    rows, audit = REF.clean(STUDENT)
    result = REF.build_result(rows, audit)
    assert (result['completion_specific_denominator'], result['completion_successes']) == (1193, 945)
    assert result['shared_three_information']['n'] == 1167
    assert result['shared_three_information']['completed'] == 927
    assert result['shared_three_information']['completion_rate'] == pytest.approx(927/1167)
    assert result['complete_case_denominator'] == 1158
    assert result['complete_case_successes'] == 922
    assert 'business_code' not in result['shared_three_information']['required_fields']
    assert 'business_code' in result['complete_case_required_fields']


def test_starter_import_does_not_write_outputs():
    with patch.object(Path, 'write_text', side_effect=AssertionError('Import wrote output')):
        load(STUDENT / 'lesson-03/analysis.py', 'lesson03_starter_import')


def test_starter_reports_blank_ids_separately():
    starter = load(STUDENT / 'lesson-03/analysis.py', 'lesson03_starter')
    row = {'ticket_id': 'T1', 'wait_minutes': '999', 'wait_unit': 'second', 'export_revision': '1'}
    out = starter.build_overview([row, {**row, 'ticket_id': ''}, {**row, 'ticket_id': None}])
    assert (out['raw_rows'], out['unique_ticket_ids'], out['blank_ticket_id_rows']) == (3, 1, 2)


def test_starter_empty_overview_is_explicit():
    starter = load(STUDENT / 'lesson-03/analysis.py', 'lesson03_starter_empty')
    out = starter.build_overview([])
    assert (out['raw_rows'], out['unique_ticket_ids'], out['missing_wait_code_rows']) == (0, 0, 0)
    json.dumps(out, allow_nan=False)


def test_starter_does_not_silently_treat_a_missing_column_as_measured(tmp_path):
    starter = load(STUDENT / 'lesson-03/analysis.py', 'lesson03_starter_schema')
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/missing.csv').write_text('ticket_id\nT1\n', encoding='utf-8')
    with patch.object(starter, 'ROOT', tmp_path), pytest.raises(ValueError, match='缺少字段'):
        starter.read('missing.csv')


def test_independent_project_matches_reference_and_keeps_raw_values(tmp_path):
    summary = WALK.solve(STUDENT, tmp_path / 'artifacts')
    rows, audit = REF.clean(STUDENT)
    result = REF.build_result(rows, audit)
    assert [summary[k] for k in ('raw_rows', 'unique_tickets', 'duplicate_rows', 'superseded_rows')] == [1265,1200,39,26]
    assert summary['converted_from_seconds'] == 42
    assert summary['tickets_with_any_issue'] == 42
    assert sum(summary['issue_counts'].values()) == 43
    assert summary['served_wait']['n'] == result['served_valid_wait']['n'] == 1122
    assert summary['served_wait']['mean_minutes'] == pytest.approx(result['served_valid_wait']['mean'])
    assert summary['shared_three']['rate'] == pytest.approx(result['shared_three_information']['completion_rate'])
    assert summary['shared_five']['rate'] == pytest.approx(result['complete_case_completion_rate'])
    with (tmp_path/'artifacts/cleaned.csv').open(encoding='utf-8', newline='') as stream:
        cleaned = list(csv.DictReader(stream))
    assert len(cleaned) == 1200
    assert any(row['wait_minutes'] in ('999','-1') and row['wait_normalized_minutes'] == '' for row in cleaned)
    with (tmp_path/'artifacts/row_handling.csv').open(encoding='utf-8', newline='') as stream:
        trace = list(csv.DictReader(stream))
    assert len(trace) == 1265
    assert {r['disposition'] for r in trace} == {'selected','superseded','duplicate'}


def test_mock_submission_runs_and_reproduces_in_a_disposable_student_repository(tmp_path):
    root = tmp_path/'student'
    shutil.copytree(STUDENT/'data/service', root/'data/service')
    (root/'lesson-03').mkdir()
    # Simulate a student's independent solution, without copying teacher imports.
    shutil.copyfile(Path(__file__).with_name('walkthrough.py'), root/'lesson-03/analysis.py')
    output = root/'lesson-03/artifacts'
    command = [sys.executable, str(root/'lesson-03/analysis.py'), '--student-root', '.', '--output', 'lesson-03/artifacts']
    subprocess.run(command, cwd=root, check=True, capture_output=True, timeout=30)
    artifacts = [f'lesson-03/artifacts/{name}' for name in ('cleaned.csv','row_handling.csv','issues.csv','summary.json')]
    manifest = {'lesson':'lesson-03','status':'complete','report':'lesson-03/artifacts/practice_report.md',
                'artifacts':artifacts,'run':['python','lesson-03/analysis.py','--student-root','.','--output','lesson-03/artifacts']}
    (root/'lesson-03/submission.json').write_text(json.dumps(manifest),encoding='utf-8')
    course = load(STUDENT/'scripts/course.py', 'lesson03_real_course_tool')
    course.check(root, 'lesson-03')
    course.ci(root, 'refs/tags/v2-l03-final')  # Deletes copied outputs and reruns on another temporary copy.
    assert json.loads((output/'summary.json').read_text())['shared_three']['n'] == 1167
    assert json.loads((STUDENT/'lesson-03/submission.json').read_text())['status'] == 'not_started'


def test_walkthrough_cannot_write_into_source_data():
    with pytest.raises(ValueError, match='separate'):
        WALK.solve(STUDENT, STUDENT/'data/service')
