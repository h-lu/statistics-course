"""R2 content, calculations and version isolation; no live service or student data.

From stat-check/: python -m pytest tests/test_r2_question_banks.py -q
These tests check explicit contracts, not student comprehension or item difficulty.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace
import json
import statistics

import pytest
import yaml

from app import db
from app.questions import BANKS, QuestionBank, load_question_banks, select_current_banks

R2 = tuple(BANKS[f"v2-l{n:02d}-r2"] for n in range(1, 9))
QUESTIONS = [(bank, item, phase) for bank in R2 for item in bank.items for phase in ("a", "b")]
PAIRS = [(bank, item) for bank in R2 for item in bank.items]


def question(number, concept, phase):
    return R2[number-1].question(concept, phase)


def correct_text(number, concept, phase):
    q = question(number, concept, phase)
    return next(option["text"] for option in q["options"] if option["id"] == q["answer"])


@pytest.mark.parametrize("bank,item,phase", QUESTIONS,
                         ids=[f"{b.lesson_id}/{i['concept_id']}/{p}" for b, i, p in QUESTIONS])
def test_each_question_has_four_distinct_options_and_diagnostic_feedback(bank, item, phase):
    q = item["pair"][phase]
    assert [o["id"] for o in q["options"]] == list("ABCD")
    assert len({o["text"].strip() for o in q["options"]}) == 4
    assert [o["id"] for o in q["options"] if o["misconception"] is None] == [q["answer"]]
    wrong = [o["misconception"] for o in q["options"] if o["id"] != q["answer"]]
    assert len(set(wrong)) == 3 and all(wrong)
    assert all("alternative-" not in name for name in wrong)
    assert q["prompt"].strip() and q["explanation"].strip() and item["tutor_context"].strip()
    assert q["explanation"] != q["answer"]
    # Current renderer shows plain text; do not require a table, code block or link.
    assert "```" not in q["prompt"] and "http" not in q["prompt"]
    json.dumps(q, ensure_ascii=False, allow_nan=False)


@pytest.mark.parametrize("bank,item", PAIRS,
                         ids=[f"{b.lesson_id}/{i['concept_id']}" for b, i in PAIRS])
def test_a_b_are_different_tasks_not_an_option_reordering(bank, item):
    a, b = item["pair"]["a"], item["pair"]["b"]
    assert a["prompt"] != b["prompt"]
    assert {o["text"] for o in a["options"]} != {o["text"] for o in b["options"]}
    # These checks supplement the documented human/AI reading, not prove equivalence.


@pytest.mark.parametrize("bank", R2, ids=[b.lesson_id for b in R2])
def test_five_pairs_durations_and_answer_positions(bank):
    assert len(bank.items) == 5 and len(set(bank.concept_ids)) == 5
    assert bank.durations == {"attempt_a": 300, "learn": 240, "attempt_b": 300}
    positions = Counter(item["pair"][p]["answer"] for item in bank.items for p in ("a", "b"))
    assert set(positions) == set("ABCD") and max(positions.values()) <= 3


@pytest.mark.parametrize("bank", R2, ids=[b.lesson_id for b in R2])
def test_teacher_and_runtime_copies_are_byte_identical(bank):
    teacher = Path(__file__).resolve().parents[2] / "instructor-guide/knowledge-check/question-bank"
    if not teacher.is_dir():
        pytest.skip("Standalone stat-check checkout does not include the teacher mirror")
    assert bank.path.read_bytes() == (teacher / bank.path.name).read_bytes()


def stubs(*ids):
    return tuple(SimpleNamespace(lesson_id=identifier) for identifier in ids)


def test_partial_upgrade_keeps_thirty_two_lessons_in_numeric_order():
    banks = stubs(*[f"v2-l{n:02d}-r1" for n in range(1, 33)],
                  *[f"v2-l{n:02d}-r2" for n in range(1, 9)], "bootcamp-01")
    assert [b.lesson_id for b in select_current_banks(tuple(reversed(banks)))] == [
        f"v2-l{n:02d}-r{2 if n <= 8 else 1}" for n in range(1, 33)]
    assert len(banks) == 41  # Selection did not remove history from the input catalog.


def test_revision_is_numeric_not_lexicographic():
    result = select_current_banks(stubs("v2-l01-r2", "v2-l01-r10", "v2-l01-r9"))
    assert [b.lesson_id for b in result] == ["v2-l01-r10"]


def test_unversioned_fallback_is_per_lesson():
    result = select_current_banks(stubs("v2-l09", "v2-l01", "v2-l01-r2"))
    assert [b.lesson_id for b in result] == ["v2-l01-r2", "v2-l09"]


def test_legacy_only_catalog_keeps_original_fallback_order():
    banks = stubs("bootcamp-02", "bootcamp-01")
    assert select_current_banks(banks) == banks
    assert select_current_banks(()) == ()


def test_loader_keeps_two_different_answer_keys_for_two_version_ids(tmp_path):
    # Synthetic historical fixture: not a replacement for a published bank.
    current = yaml.safe_load(R2[0].path.read_text(encoding="utf-8"))
    old = deepcopy(current)
    old["lesson_id"] = "v2-l01-r1"
    old_q = old["items"][0]["pair"]["a"]
    old_q["answer"] = next(letter for letter in "ABCD" if letter != old_q["answer"])
    for option in old_q["options"]:
        option["misconception"] = None if option["id"] == old_q["answer"] else "fixture-error"
    for filename, value in (("lesson-old.yml", old), ("lesson-new.yml", current)):
        (tmp_path / filename).write_text(yaml.safe_dump(value, allow_unicode=True), encoding="utf-8")
    loaded = load_question_banks(tmp_path)
    by_id = {b.lesson_id: b for b in loaded}
    assert len(loaded) == 2 and len(select_current_banks(loaded)) == 1
    assert select_current_banks(loaded)[0].lesson_id == "v2-l01-r2"
    concept = old["items"][0]["concept_id"]
    assert by_id["v2-l01-r1"].question(concept, "a")["answer"] == old_q["answer"]
    assert by_id["v2-l01-r1"].question(concept, "a")["answer"] != by_id["v2-l01-r2"].question(concept, "a")["answer"]


def test_loader_rejects_duplicate_version_id(tmp_path):
    for filename in ("lesson-first.yml", "lesson-second.yml"):
        (tmp_path / filename).write_bytes(R2[0].path.read_bytes())
    with pytest.raises(ValueError, match="unique"):
        load_question_banks(tmp_path)


def test_reinitialization_keeps_existing_session_responses_and_learning(tmp_path):
    # Uses the real unchanged SQLite module, but only an explicit test database.
    path = str(tmp_path / "history.sqlite3")
    db.initialize(path, "history-fixture", "历史隔离测试")
    old_session = dict(db.current_session(path))
    user = db.upsert_user(path, gitea_id=101, login="fixture", display_name="测试", role="student")
    db.save_response(path, session_id=old_session["id"], user_id=user["id"],
                     concept_id="unit", phase="a", option_id="A", confidence="unsure", correct=False)
    db.mark_learning_complete(path, old_session["id"], user["id"])
    old_response = dict(db.responses_for_user(path, old_session["id"], user["id"])[0])
    db.initialize(path, R2[0].lesson_id, R2[0].title)
    assert dict(db.current_session(path)) == old_session
    new_session = db.create_session(path, R2[0].lesson_id, R2[0].title)
    assert new_session["id"] != old_session["id"]
    assert dict(db.responses_for_user(path, old_session["id"], user["id"])[0]) == old_response
    assert db.learning_complete(path, old_session["id"], user["id"])
    assert not db.responses_for_user(path, new_session["id"], user["id"])


@pytest.mark.parametrize("bank", R2, ids=[b.lesson_id for b in R2])
def test_each_new_bank_can_complete_backend_a_learning_b_and_export(tmp_path, bank):
    path = str(tmp_path / "flow.sqlite3")
    db.initialize(path, bank.lesson_id, bank.title)
    session = db.current_session(path)
    user = db.upsert_user(path, gitea_id=1, login="fixture", display_name="测试", role="student")
    for phase in ("a", "b"):
        for item in bank.items:
            q = item["pair"][phase]
            db.save_response(path, session_id=session["id"], user_id=user["id"],
                             concept_id=item["concept_id"], phase=phase, option_id=q["answer"],
                             confidence="sure", correct=True)
    db.mark_learning_complete(path, session["id"], user["id"])
    assert len(db.responses_for_user(path, session["id"], user["id"])) == 10
    assert db.dashboard_summary(path, session["id"], 5)["completed"] == {"a": 1, "b": 1, "learn": 1}
    row = db.export_rows(path, session["id"])[0]
    assert (row["a_correct"], row["b_correct"], row["learned"]) == (5, 5, 1)


# Independently written calculations for numerical/decision items. Each case
# checks the calculation and the text of the selected option, not just its letter.
CALCULATIONS = [
    (1, "unit", "a", lambda: F(2+6+10, 2), F(9), "＝9分钟"),
    (1, "location", "a", lambda: (statistics.mean([2,4,6,8,80]), statistics.median([2,4,6,8,80])), (20,6), "均值从10变为20分钟，中位数仍为6"),
    (1, "location", "b", lambda: F(2+4+6+8, 4), F(5), "平均等待5分钟"),
    (2, "quantile", "a", lambda: 20+F(1,4)*(30-20), F(45,2), "22.5"),
    (2, "dispersion", "a", lambda: statistics.pstdev([7,9,11])-statistics.pstdev([2,4,6]), 0, "标准差不变"),
    (2, "dispersion", "b", lambda: (2*60, 3*60), (120,180), "120秒和180秒"),
    (3, "missing-units", "b", lambda: F(0+12,2), F(6), "6件，采用2条"),
    (3, "purpose-denominator", "a", lambda: 100-2, 98, "98张"),
    (3, "selection-cleaning", "a", lambda: (F(80,100),F(54,60)), (F(4,5),F(9,10)), "80%描述全部工单，90%描述所选60张"),
    (4, "iqr-robustness", "a", lambda: 5-5, 0, "两个四分位数相等"),
    (4, "composite", "b", lambda: F(12*60,600), F(12,10), "秒数÷600"),
    (4, "goal-metric", "a", lambda: F(3+4-2,10), F(1,2), "5÷10＝50%"),
    (4, "goal-metric", "b", lambda: (F(sum(v>15 for v in [15,15,16]+[5]*7),10)>F(1,10)), False, "10%，没有触发"),
    (5, "ecdf", "b", lambda: F(sum(v<=20 for v in [10,20,20,50]),4), F(3,4), "3÷4＝75%"),
    (5, "capacity-ties", "a", lambda: 10-8, 2, "最多再选2台"),
    (5, "capacity-ties", "b", lambda: sorted(zip([60,95,85],['D1','D2','D3']),reverse=True)[0][1], "D2", "甲日D1、D2；乙日D2"),
    (5, "fpr", "a", lambda: F(40-18,120-30), F(11,45), "22÷90"),
    (5, "fpr", "b", lambda: 10-10, 0, "不能计算"),
    (5, "fnr", "a", lambda: F(10-7,10), F(3,10), "3÷10＝30%"),
    (5, "fnr", "b", lambda: F(2,3+2), F(2,5), "2÷5＝40%"),
    (5, "loss-action", "a", lambda: 100+100*(1-F(85,100))+2*2, F(119), "119个成本单位"),
    (5, "loss-action", "b", lambda: (200+40,2*60+40), (240,160), "160，低于甲的240"),
    (6, "marginal", "a", lambda: F(8+50,10+100), F(29,55), "58÷110"),
    (6, "marginal", "b", lambda: F(80+60,100+300), F(7,20), "＝35%"),
    (6, "standardization", "b", lambda: F(4,10)*F(9,10)+F(6,10)*F(7,10), F(39,50), "78%"),
    (6, "simpson", "b", lambda: (F(1,2)*20+F(1,2)*5,F(1,4)*20+F(3,4)*5), (F(25,2),F(35,4)), "从12.5变为8.75个百分点"),
    (7, "response-denominator", "a", lambda: F(60,120), F(1,2), "60÷120＝50%"),
    (7, "complete-cases", "a", lambda: F(48,60), F(4,5), "满意比例为80%"),
    (7, "imputation", "a", lambda: F(40,100)*F(8,10)+F(60,100)*F(18,30), F(17,25), "＝68%"),
    (7, "bounds", "a", lambda: (F(30,100),F(30+60,100)), (F(3,10),F(9,10)), "30%至90%"),
    (7, "bounds", "b", lambda: (200*F(7,10)-60)/100, F(4,5), "80%"),
    (8, "cardinality", "a", lambda: 200+50, 250, "追加为250张"),
    (8, "duplication", "a", lambda: (F(4+4+16,3), F(4+16,2)), (F(8),F(10)), "工单权重改变"),
    (8, "duplication", "b", lambda: 100+100, 200, "得到200元"),
    (8, "unmatched", "b", lambda: 8+8, 16, "16人时"),
    (8, "reconciliation", "a", lambda: 2*4-1, 7, "＝7人时"),
    (8, "reconciliation", "b", lambda: 7+5, 12, "12人时"),
]


@pytest.mark.parametrize("number,concept,phase,calculate,expected,fragment", CALCULATIONS,
                         ids=[f"L{n:02d}/{c}/{p}" for n,c,p,*_ in CALCULATIONS])
def test_numerical_answer_and_selected_option(number, concept, phase, calculate, expected, fragment):
    assert calculate() == expected
    assert fragment in correct_text(number, concept, phase)
