"""调查覆盖、界限与情景计算；假设和补采决定由学生提出。"""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(name):
    with (ROOT / "data" / "service" / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def rate(num, den):
    return num / den if den else None


def records():
    tickets = read("tickets.csv")
    ids = [row["ticket_id"] for row in tickets]
    if len(ids) != len(set(ids)) or any(not value.strip() for value in ids):
        raise ValueError("目标工单编号为空或重复")
    surveys = {}
    for row in read("satisfaction.csv"):
        if row["ticket_id"] in surveys or not row["ticket_id"].strip():
            raise ValueError("调查编号为空或重复")
        surveys[row["ticket_id"]] = row
    result = []
    for ticket in tickets:
        survey = surveys.get(ticket["ticket_id"])
        invitation = (survey.get("invited", "") if survey else "").strip()
        raw_score = (survey.get("score", "") if survey else "").strip()
        if invitation not in ("", "0", "1") or raw_score not in ("", "1", "2", "3", "4", "5"):
            raise ValueError("未知邀请或评分编码须先核对")
        if invitation == "0" and raw_score:
            raise ValueError("未受邀却有评分，须先核对")
        state = "unmatched" if survey is None else "unknown_invitation" if invitation == "" else "uninvited" if invitation == "0" else "responded" if raw_score else "invited_nonresponse"
        wait = float(ticket["wait_minutes"])
        if not math.isfinite(wait) or wait < 0 or ticket["abandoned"] not in ("0", "1"):
            raise ValueError("办理经历编码异常")
        result.append({**ticket, "invited": int(invitation) if invitation else None,
                       "score": int(raw_score) if raw_score else None, "state": state, "wait": wait,
                       "survey_matched": survey is not None})
    return result


def overview(rows, happy_cutoff):
    states = Counter(row["state"] for row in rows)
    invited = sum(row["invited"] == 1 for row in rows)
    replied = [row for row in rows if row["score"] is not None]
    invited_replied = sum(row["invited"] == 1 for row in replied)
    happy = sum(row["score"] >= happy_cutoff for row in replied)
    n, missing = len(rows), len(rows) - len(replied)
    unknown = states["unmatched"] + states["unknown_invitation"]
    features = []
    for state in ("uninvited", "invited_nonresponse", "responded", "unmatched", "unknown_invitation"):
        group = [row for row in rows if row["state"] == state]
        features.append({"state": state, "n": len(group), "case_n": sum(row["business_code"] == "case" for row in group),
                         "abandoned_n": sum(row["abandoned"] == "1" for row in group),
                         "mean_wait_minutes": statistics.mean(row["wait"] for row in group) if group else None,
                         "median_wait_minutes": statistics.median(row["wait"] for row in group) if group else None})
    return {"target_tickets": n, "matched_surveys": n - states["unmatched"], "unmatched_tickets": states["unmatched"],
            "unknown_invitation": states["unknown_invitation"], "states": dict(states), "invited": invited,
            "responded": len(replied), "invited_responded": invited_replied, "satisfied_at_least": happy_cutoff,
            "satisfied": happy, "missing_score": missing, "observed_score_counts": dict(Counter(row["score"] for row in replied)),
            "invitation_rate": rate(invited, n) if unknown == 0 else None,
            "invitation_rate_bounds": [rate(invited, n), rate(invited + unknown, n)],
            "response_among_known_invited": rate(invited_replied, invited), "response_among_all": rate(len(replied), n),
            "respondent_satisfied_rate": rate(happy, len(replied)),
            "bounds_for_unknown_scores": [rate(happy, n), rate(happy + missing, n)], "known_features_by_state": features}


def unknown_score_bounds(happy, responded, target):
    """固定目标与有效已知回答时，未知评分造成的逻辑界限。"""
    if not 0 <= happy <= responded <= target:
        raise ValueError("须满足0≤满意数≤回答数≤目标数")
    return [rate(happy, target), rate(happy + target - responded, target)]


def weighted_rate(rates, weights):
    """按学生自选层及权重合并比例；零回答层须保留None。"""
    if set(rates) != set(weights) or any(not math.isfinite(w) or w < 0 for w in weights.values()) or not math.isclose(sum(weights.values()), 1):
        raise ValueError("权重标签须相同、非负且合计为1")
    total = 0.0
    for key, weight in weights.items():
        if weight == 0:
            continue
        p = rates[key]
        if p is None:
            return None
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("比例须在0到1或为None")
        total += weight * p
    return total


def main():
    result = overview(records(), 4)
    result["note"] = "只核对调查起点与有效已知评分。满意定义、情景、调整、发布和补采由学生自行组织。"
    (HERE / "artifacts").mkdir(exist_ok=True)
    path = HERE / "artifacts" / "starting_overview.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
