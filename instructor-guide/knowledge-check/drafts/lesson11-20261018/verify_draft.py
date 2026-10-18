#!/usr/bin/env python3
"""Read-only draft verification; never import the application or open a database.

Run from any directory with Python 3 and the course's existing PyYAML dependency.
Writes a local teacher audit JSON next to this script; no runtime installation.
The independent reference calculations below are separate from the bank text.
"""
from __future__ import annotations

import ast
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BANK = HERE / "lesson-v2r3-11-20261018.yml"
QUESTION_MODULE = ROOT / "stat-check/app/questions.py"
EXPECTED_ID = "v2-l11-r3-20261018"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ratio(positive: int, total: int):
    if total == 0:
        return None
    return F(positive, total)


def verify():
    raw = json.loads(BANK.read_text(encoding="utf-8"))
    assert yaml.safe_load(BANK.read_text(encoding="utf-8")) == raw
    assert raw["lesson_id"] == EXPECTED_ID
    assert raw["duration_seconds"] == {
        "attempt_a": 300, "learn": 240, "attempt_b": 300
    }
    assert len(raw["items"]) == 5

    # Extract only the existing pure data-validator class. Do not execute the
    # module's top-level bank registry, import the web app, or open any database.
    tree = ast.parse(QUESTION_MODULE.read_text(encoding="utf-8"))
    classes = [
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "QuestionBank"
    ]
    assert len(classes) == 1
    namespace = {"Path": Path, "yaml": yaml}
    exec(compile(ast.Module(body=classes, type_ignores=[]),
                 str(QUESTION_MODULE), "exec"), namespace)
    validated = namespace["QuestionBank"](BANK)
    assert validated.lesson_id == EXPECTED_ID
    assert validated.concept_ids == [
        f"l11-r3-20261018-c{i}" for i in range(1, 6)
    ]

    # No preexisting/active/archived bank may reuse the new immutable ID.
    # The script ignores its own audit JSON and searches YAML content only.
    matches = [
        path for path in ROOT.rglob("*.yml")
        if EXPECTED_ID in path.read_text(encoding="utf-8")
    ]
    assert matches == [BANK], [str(p.relative_to(ROOT)) for p in matches]
    assert BANK.parent == HERE
    assert "drafts" in BANK.parts
    assert not (ROOT / "stat-check/app/question_bank" / BANK.name).exists()
    assert not (ROOT / "instructor-guide/knowledge-check/question-bank" / BANK.name).exists()

    # Independent hand-calculation references and statistical arguments.
    references = {}
    # c1a: disjoint stages under the stated frame/invitation assumptions.
    assert 3200 + 800 == 4000
    assert 4000 - 3500 == 500
    assert 3500 - 200 == 3300
    assert 200 - 120 == 80
    references["c1a"] = {
        "answer": "B",
        "calculation": {"target": 4000, "frame": 3500,
                        "invited": 200, "responded": 120,
                        "frame_not_invited": 3300,
                        "undercovered": 500, "unit_nonresponse": 80},
        "rationale": "Target is fixed by the question; frame, invitation and response are distinct stages."
    }
    references["c1b"] = {
        "answer": "A",
        "calculation": {
            "Zhou": {"in_target": True, "in_frame": True,
                     "invited": False, "unit_nonresponse": False},
            "Li": {"in_target": True, "in_frame": True,
                   "invited": True, "responded": False,
                   "unit_nonresponse": True}},
        "rationale": "No answer row does not identify which acquisition stage excluded a person."
    }
    assert F(200, 3200) > 0 and F(0, 800) == 0
    references["c2a"] = {
        "answer": "D",
        "calculation": {"A_invitation_probability": str(F(200, 3200)),
                        "B_invitation_probability": "0"},
        "rationale": "Random selection within a frame cannot give positive invitation probability to an absent group."
    }
    assert F(12, 60) == F(1, 5) and F(12, 60) != F(12, 48)
    references["c2b"] = {
        "answer": "C",
        "calculation": {"pre_draw_probability": "1/5", "percent": 20},
        "rationale": "A realized nonselection is compatible with a positive pre-draw inclusion probability."
    }
    assert ratio(24, 40) == F(3, 5)
    assert ratio(24, 200) == F(3, 25)
    assert ratio(24, 4000) == F(3, 500)
    # Among invitees alone, the 160 missing outcomes could be all 0 or all 1.
    assert ratio(24, 200) != ratio(24 + 160, 200)
    references["c3a"] = {
        "answer": "A",
        "calculation": {"respondent_rate": "3/5",
                        "invitee_rate_if_missing_all_zero": "3/25",
                        "invitee_rate_if_missing_all_one": "23/25"},
        "rationale": "Only the respondent fraction is observed; random invitations do not identify missing outcomes."
    }
    assert F(40, 80) == F(1, 2)
    assert F(30, 30 + 10) == F(3, 4)
    assert F(30, 40) != F(10, 40)
    references["c3b"] = {
        "answer": "D",
        "calculation": {"invitee_intention_rate": "1/2",
                        "respondent_intention_rate": "3/4",
                        "response_rate_intending": "3/4",
                        "response_rate_not_intending": "1/4"},
        "rationale": "Outcome-dependent response changes composition after random invitation; full outcomes here are a declared simulation audit."
    }
    weighted = F(90, 120) * F(6, 15) + F(30, 120) * F(12, 15)
    unweighted = F(6 + 12, 15 + 15)
    assert weighted == F(1, 2) and unweighted == F(3, 5)
    # Feasible within-group selection counterexample: actual needs 18/90 and
    # 12/30 coexist with the question's respondent outcomes 6/15 and 12/15.
    selected_true = F(90, 120) * F(18, 90) + F(30, 120) * F(12, 30)
    assert selected_true == F(1, 4) and selected_true != weighted
    references["c4a"] = {
        "answer": "C",
        "calculation": {"X_respondent_rate": "2/5",
                        "Y_respondent_rate": "4/5",
                        "population_share_weighted_rate": "1/2",
                        "unweighted_rate": "3/5",
                        "counterexample_true_rate_under_within_group_selection": "1/4"},
        "rationale": "Known group shares fix inter-group composition, conditional on usable within-group rates; they do not remove all selection."
    }
    assert ratio(0, 0) is None
    old_rate = F(8, 20)
    possible1 = F(3, 10) * 0 + F(7, 10) * old_rate
    possible2 = F(3, 10) * 1 + F(7, 10) * old_rate
    assert possible1 == F(7, 25) and possible2 == F(29, 50)
    assert possible1 != possible2
    references["c4b"] = {
        "answer": "B",
        "calculation": {"new_respondent_rate": None,
                        "old_respondent_rate": "2/5",
                        "if_unobserved_new_rate_zero": "7/25",
                        "if_unobserved_new_rate_one": "29/50"},
        "rationale": "A missing group produces an undefined 0/0 rate; known group share alone cannot identify its outcome rate."
    }
    assert 120 * F(1, 4) == 30
    assert 120 * F(3, 5) == 72
    assert (120 * 1, 120 * 4) == (120, 480)
    references["c5a"] = {
        "answer": "A",
        "calculation": {"email_expected_responses": 30,
                        "telephone_expected_responses": 72,
                        "email_invitation_cost_yuan": 120,
                        "telephone_invitation_cost_yuan": 480},
        "rationale": "Fixed invitation count does not fix expected response count, cost or representativeness; expectations are not realized guarantees."
    }
    assert (200 // 2, 200 // 5) == (100, 40)
    assert (100 * F(1, 5), 40 * F(1, 2)) == (20, 20)
    references["c5b"] = {
        "answer": "B",
        "calculation": {"email_invitations": 100,
                        "telephone_invitations": 40,
                        "email_expected_responses": 20,
                        "telephone_expected_responses": 20},
        "rationale": "Equal budgets may produce different invitation counts; equal expected replies do not identify the sampling or response mechanism."
    }

    wrong_ids = []
    all_keys = []
    records = []
    for i, item in enumerate(raw["items"], 1):
        for phase in ("a", "b"):
            question = item["pair"][phase]
            reference = references[f"c{i}{phase}"]
            assert question["answer"] == reference["answer"]
            assert [o["id"] for o in question["options"]] == list("ABCD")
            assert len({o["text"] for o in question["options"]}) == 4
            correct = [o for o in question["options"]
                       if o["misconception"] is None]
            assert len(correct) == 1 and correct[0]["id"] == reference["answer"]
            for option in question["options"]:
                if option["id"] != reference["answer"]:
                    diagnostic = option["misconception"]
                    assert diagnostic.startswith(f"l11-c{i}-{phase}-")
                    assert diagnostic != option["text"]
                    wrong_ids.append(diagnostic)
            assert not any(field in question for field in ("points", "score"))
            all_keys.append(reference["answer"])
            records.append({"concept_id": item["concept_id"], "phase": phase,
                            **reference})
        assert item["pair"]["a"]["prompt"] != item["pair"]["b"]["prompt"]
    assert len(wrong_ids) == 30 and len(set(wrong_ids)) == 30
    counts = dict(sorted(Counter(all_keys).items()))
    assert counts == {"A": 3, "B": 3, "C": 2, "D": 2}
    return {
        "status": "passed",
        "lesson_id": EXPECTED_ID,
        "release_state": "offline draft only; not registered, installed or deployed",
        "bank_relative_path": str(BANK.relative_to(ROOT)),
        "bank_sha256": sha256(BANK),
        "questions_source_sha256": sha256(QUESTION_MODULE),
        "format": "JSON-compatible YAML, existing QuestionBank class validated in isolation",
        "pure_validation": {
            "app_imported": False, "database_opened": False,
            "runtime_registry_executed": False, "runtime_copy_created": False},
        "concepts": 5, "questions": 10, "options": 40,
        "unique_wrong_option_diagnostics": 30,
        "correct_letter_counts": counts,
        "duration_seconds": raw["duration_seconds"],
        "grading_policy_changed": False,
        "independent_references": records,
        "limitations": [
            "QuestionBank format and exact rational arithmetic do not establish equal A/B difficulty or diagnostic performance.",
            "No real-student reading or classroom timing trial has been performed.",
            "These hypothetical concept examples do not reveal formal population outcomes, select an automatic optimal design, or establish causal or inference guarantees.",
            "No student-facing question/answer copies, runtime registration, database writes, deployment, commit or push are performed by this script."
        ]
    }


if __name__ == "__main__":
    result = verify()
    (HERE / "audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "status", "lesson_id", "bank_sha256", "questions",
        "unique_wrong_option_diagnostics", "correct_letter_counts")},
        ensure_ascii=False, indent=2))
