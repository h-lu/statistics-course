"""Check the approved student reading example against fresh local acquisitions."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LESSON = ROOT / "student-template/lesson-11"
sys.path.insert(0, str(LESSON))
import sampling_tools as tools


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rejected(call):
    try:
        call()
    except (ValueError, FileExistsError) as error:
        return type(error).__name__ + ": " + str(error)
    raise AssertionError("Invalid operation was accepted")


def main():
    before = {str(p.relative_to(ROOT)): sha(p) for p in [
        LESSON / name for name in ("README.md", "LEARN.md", "SUPPORT.md", "sampling_tools.py")
    ]}
    frame = tools.load_frame()
    plans = {mode: tools.make_request(frame, mode, 200, 11, 11)
             for mode in ("register_ordinary", "web_voluntary")}
    operations = {}
    failures = {}
    temporary_parent = ROOT.parents[0] / "audit/tmp"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="student-path-final-", dir=temporary_parent) as temporary:
        temporary = Path(temporary)
        for mode, plan in plans.items():
            tools.write_request(plan, temporary / f"{mode}-preplan.json")
        for mode, plan in plans.items():
            rows, receipt = tools.run_request(plan, temporary / mode)
            assert len(rows) == 4000
            assert tools.read_observations(temporary / mode / "observations.csv") == rows
            assert all(r["observed_need"] is None for r in rows if not r["answered"])
            stored = HERE / "reference-seed11" / mode
            for name in ("request.json", "observations.csv", "receipt.json"):
                assert (temporary / mode / name).read_bytes() == (stored / name).read_bytes()
            operations[mode] = {"invited": receipt["invited"], "responded": receipt["responded"],
                                "invitation_cost_units": receipt["invitation_cost_units"],
                                "observations_sha256": receipt["observations_sha256"],
                                "all_4000_rows_csv_roundtrip": True,
                                "all_unobserved_outcomes_none": True,
                                "matches_saved_teacher_snapshot": True}
            failures[f"{mode}-existing-output"] = rejected(lambda: tools.run_request(plan, temporary / mode))
            if mode == "web_voluntary":
                by_id = {r["person_id"]: r for r in rows}
                expected = {"A0002": (0, 0, 0, None), "A0001": (1, 0, 0, None),
                            "A0004": (1, 1, 0, None), "A0003": (1, 1, 1, 1)}
                for person, values in expected.items():
                    row = by_id[person]
                    assert tuple(row[key] for key in ("in_frame", "invited", "answered", "observed_need")) == values
                    assert row["invite_probability"] == (200 / 3305 if row["in_frame"] else 0)
                operations[mode]["learn_section8_rows"] = {person: by_id[person] for person in expected}
                operations[mode]["positive_invitation_chance_percent"] = 100 * 200 / 3305
        failures["zero-n"] = rejected(lambda: tools.make_request(frame, "register_ordinary", 0, 11, 11))
        failures["web-frame-overflow"] = rejected(lambda: tools.make_request(frame, "web_voluntary", 3306, 11, 11))
        failures["latent-table-as-planning-frame"] = rejected(lambda: tools.load_frame(LESSON / "data/simulator/weekend_population.csv"))
        changed = dict(plans["web_voluntary"], response_seed=12)
        failures["changed-plan-at-audit"] = rejected(lambda: tools.audit_population(changed, temporary / "web_voluntary"))
        rows = [{"group": "A", "answered": 1, "observed_need": 1}]
        assert tools.composition_estimate(rows, {"A": 3200, "B": 800}) is None
    protection = json.loads((HERE / "previous-material-protection.json").read_text())
    for relative, digest in protection["files_sha256"].items():
        assert sha(ROOT / relative) == digest, relative
    draft = ROOT / "instructor-guide/knowledge-check/drafts/lesson11-20261018/lesson-v2r3-11-20261018.yml"
    assert sha(draft) == "97fce20fb82fe2fcbca2fe77085a67879680d17ac64256088aa24e4c07f44b54"
    after = {relative: sha(ROOT / relative) for relative in before}
    assert after == before
    section8 = (LESSON / "LEARN.md").read_text().split("## 8.", 1)[1]
    assert "41%" not in section8 and "0.41" not in section8
    record = {"passed": True, "scope": "Fresh local synthetic acquisitions and read-only student-path checks; no production operations",
              "approved_draft_sha256_unchanged": sha(draft), "protected_previous_files_unchanged": len(protection["files_sha256"]),
              "student_reading_sources_unchanged_by_test": before,
              "main_mechanism_runs": operations, "invalid_operations_rejected": failures,
              "missing_response_group_estimate": None, "section8_does_not_fill_formal_comparison_or_truth": True,
              "cost_basis": "New L11 invitation assumption A=1/B=3; not historical complete-contact prices or real business costs"}
    (HERE / "final-student-path-check.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": True, "main_mechanisms": 2, "formal_rows_checked": 8000,
                      "invalid_operations_rejected": len(failures), "previous_files_unchanged": len(protection["files_sha256"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
