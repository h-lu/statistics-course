"""Observed responses, bounds for unknown scores and explicit scenarios."""
from pathlib import Path
from collections import defaultdict
import importlib.util
spec = importlib.util.spec_from_file_location("shared_reference", Path(__file__).resolve().parents[1] / "lesson-01" / "reference.py")
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def attach_surveys(rows, surveys):
    """Retain every target ticket; a missing survey is not an uninvited ticket."""
    survey = u.keyed(surveys, "ticket_id")
    records = []
    for row in rows:
        source = survey.get(row["ticket_id"])
        # A numeric 0 is a recorded value, not missing. The parser also serves L08.
        invited_value = (source or {}).get("invited")
        score_value = (source or {}).get("score")
        raw_invited = "" if invited_value is None else str(invited_value).strip()
        raw_score = "" if score_value is None else str(score_value).strip()
        if raw_invited not in ("", "0", "1"):
            raise ValueError(f"Invalid invitation status: {row['ticket_id']}")
        if raw_score not in ("", "1", "2", "3", "4", "5"):
            raise ValueError(f"Invalid satisfaction score: {row['ticket_id']}")
        if raw_invited == "0" and raw_score:
            raise ValueError(f"Uninvited ticket has a score; verify survey: {row['ticket_id']}")
        records.append({**row, "survey_matched": source is not None,
                        "invited": int(raw_invited) if raw_invited else None,
                        "score": int(raw_score) if raw_score else None})
    return records


def build_result(rows, surveys):
    records = attach_surveys(rows, surveys)
    n = len(records)
    invited = sum(r["invited"] == 1 for r in records)
    replied = [r for r in records if r["score"] is not None]
    invited_replies = sum(r["invited"] == 1 for r in replied)
    happy = sum(r["score"] >= 4 for r in replied)
    missing = n - len(replied)
    unmatched = sum(not r["survey_matched"] for r in records)
    unknown_invitation = sum(r["survey_matched"] and r["invited"] is None for r in records)
    strata = defaultdict(list)
    for r in records:
        strata[(r["business_code"], "over15" if r["wait"] > 15 else "at_most15", r["abandon"])].append(r)
    cells, estimate, unidentified = [], 0, 0
    for key, members in sorted(strata.items()):
        known = [r for r in members if r["score"] is not None]
        satisfied = sum(r["score"] >= 4 for r in known)
        p = u.rate(satisfied, len(known))
        if p is not None:
            estimate += len(members) / n * p
        else:
            unidentified += len(members)
        cells.append({"business": key[0], "wait_group": key[1], "abandoned": key[2],
                      "target_n": len(members), "responded": len(known), "missing": len(members) - len(known),
                      "response_rate": len(known) / len(members), "observed_satisfied_rate": p})
    scenarios = [{"missing_satisfied_rate": q, "overall_satisfied_rate": u.rate(happy + missing * q, n)}
                 for q in (0, .25, .5, .75, 1)]
    return {"target_tickets": n, "invited": invited, "responded": len(replied), "satisfied_respondents": happy,
            "unmatched_surveys": unmatched, "unknown_invitation": unknown_invitation,
            "uninvited": sum(r["invited"] == 0 for r in records),
            "invited_without_response": invited - invited_replies,
            "responded_among_known_invited": invited_replies,
            "invitation_status_known": n - unmatched - unknown_invitation,
            "invitation_rate": u.rate(invited, n) if not (unmatched or unknown_invitation) else None,
            "response_among_invited": u.rate(invited_replies, invited), "response_among_all": u.rate(len(replied), n),
            "respondent_satisfied_rate": u.rate(happy, len(replied)),
            "no_assumption_bounds": [u.rate(happy, n), u.rate(happy + missing, n)], "scenarios": scenarios,
            "stratum_adjusted_under_within_cell_MAR": estimate if n and not unidentified else None,
            "target_units_in_zero_response_cells": unidentified, "cells": cells,
            "warning": "Invitation rate is unidentified when invitation status is missing; response_among_invited describes known invited tickets only. Bounds keep the target and recorded answers fixed. The adjusted value assumes respondents represent all target tickets within business/wait/abandonment cells, including uninvited and unmatched tickets. These assumptions are not established by the data."}


def main():
    root = u.student_root()
    u.emit(build_result(u.baseline(root), u.read(root, "service/satisfaction.csv")))


if __name__ == "__main__":
    main()
