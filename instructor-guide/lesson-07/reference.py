"""Observed response, sharp no-assumption bounds and explicit scenarios."""
from pathlib import Path
from collections import defaultdict
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

def main():
    root = u.student_root()
    rows = u.baseline(root)
    surveys = u.read(root, "service/satisfaction.csv")
    assert len({r["ticket_id"] for r in surveys}) == len(surveys)
    survey = {r["ticket_id"]: r for r in surveys}
    records = [{**r, "invited": int(survey[r["ticket_id"]]["invited"]), "score": int(survey[r["ticket_id"]]["score"]) if survey[r["ticket_id"]]["score"] else None} for r in rows]
    n = len(records)
    invited = sum(r["invited"] for r in records)
    replied = [r for r in records if r["score"] is not None]
    happy = sum(r["score"] >= 4 for r in replied)
    missing = n - len(replied)
    observed = happy / len(replied)
    strata = defaultdict(list)
    for r in records:
        strata[(r["business_code"], "over15" if r["wait"] > 15 else "at_most15", r["abandon"])].append(r)
    cells, estimate, unidentified = [], 0, 0
    for key, members in sorted(strata.items()):
        known = [r for r in members if r["score"] is not None]
        satisfied = sum(r["score"] >= 4 for r in known)
        p = satisfied / len(known) if known else None
        if p is not None:
            estimate += len(members) / n * p
        else:
            unidentified += len(members)
        cells.append({"business": key[0], "wait_group": key[1], "abandoned": key[2], "target_n": len(members), "responded": len(known), "missing": len(members) - len(known), "response_rate": len(known) / len(members), "observed_satisfied_rate": p})
    scenarios = [{"missing_satisfied_rate": q, "overall_satisfied_rate": (happy + missing * q) / n} for q in (0, .25, .5, .75, 1)]
    u.emit({"target_tickets": n, "invited": invited, "responded": len(replied), "satisfied_respondents": happy, "invitation_rate": invited / n, "response_among_invited": len(replied) / invited, "response_among_all": len(replied) / n, "respondent_satisfied_rate": observed, "no_assumption_bounds": [happy / n, (happy + missing) / n], "scenarios": scenarios, "stratum_adjusted_under_within_cell_MAR": estimate if not unidentified else None, "target_units_in_zero_response_cells": unidentified, "cells": cells, "warning": "The adjusted value assumes respondents represent nonrespondents within business/wait/abandonment cells. This is not established by the data."})

if __name__ == "__main__":
    main()
