from __future__ import annotations

from pathlib import Path

import yaml


class QuestionBank:
    def __init__(self, path: Path) -> None:
        self.path = path
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.lesson_id = str(raw["lesson_id"])
        self.title = str(raw["title"])
        self.durations = {
            key: int(value) for key, value in raw["duration_seconds"].items()
        }
        self.items = list(raw["items"])
        self._by_concept = {
            str(item["concept_id"]): item for item in self.items
        }
        self._validate()

    def _validate(self) -> None:
        if not self.items:
            raise ValueError("question bank has no items")
        if set(self.durations) != {"attempt_a", "learn", "attempt_b"} or any(v <= 0 for v in self.durations.values()):
            raise ValueError("question bank has invalid durations")
        concept_ids = [str(item["concept_id"]) for item in self.items]
        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError("question bank contains duplicate concept_id")
        for item in self.items:
            if not all(str(item.get(key, "")).strip() for key in ("concept_id", "title", "tutor_context")):
                raise ValueError("question bank contains empty concept text")
            if set(item["pair"]) != {"a", "b"}:
                raise ValueError(f"invalid pair: {item['concept_id']}")
            for phase in ("a", "b"):
                question = item["pair"][phase]
                question["options"] = sorted(
                    question["options"], key=lambda option: str(option["id"])
                )
                option_ids = [str(option["id"]) for option in question["options"]]
                if len(option_ids) != len(set(option_ids)):
                    raise ValueError(f"duplicate option: {item['concept_id']}")
                if str(question["answer"]) not in option_ids:
                    raise ValueError(f"missing answer: {item['concept_id']}")
                if option_ids != ["A", "B", "C", "D"]:
                    raise ValueError(f"four options A-D required: {item['concept_id']}")
                if not str(question.get("prompt", "")).strip() or not str(question.get("explanation", "")).strip():
                    raise ValueError(f"empty question text: {item['concept_id']}")
                if any(not str(option.get("text", "")).strip() for option in question["options"]):
                    raise ValueError(f"empty option text: {item['concept_id']}")

    def item(self, concept_id: str) -> dict:
        return self._by_concept[concept_id]

    def question(self, concept_id: str, phase: str) -> dict:
        return self.item(concept_id)["pair"][phase]

    @property
    def concept_ids(self) -> list[str]:
        return [str(item["concept_id"]) for item in self.items]


def load_question_banks(directory: Path) -> tuple[QuestionBank, ...]:
    banks = tuple(QuestionBank(path) for path in sorted(directory.glob("lesson-*.yml")))
    if not banks:
        raise ValueError("question bank directory is empty")
    lesson_ids = [bank.lesson_id for bank in banks]
    if len(lesson_ids) != len(set(lesson_ids)):
        raise ValueError("question bank lesson_id values must be unique")
    return banks


QUESTION_BANKS = load_question_banks(Path(__file__).parent / "question_bank")
BANKS = {bank.lesson_id: bank for bank in QUESTION_BANKS}
CURRENT_BANKS = (
    tuple(
        bank for bank in QUESTION_BANKS
        if bank.lesson_id.startswith("v2-l") and bank.lesson_id.endswith("-r1")
    )
    or tuple(bank for bank in QUESTION_BANKS if bank.lesson_id.startswith("v2-l"))
    or QUESTION_BANKS
)
DEFAULT_BANK = CURRENT_BANKS[0]


def bank_for_lesson(lesson_id: str) -> QuestionBank:
    try:
        return BANKS[lesson_id]
    except KeyError as error:
        raise LookupError(f"question bank is missing for lesson: {lesson_id}") from error


# Backwards-compatible name used by the first-lesson tests and small helper scripts.
BANK = DEFAULT_BANK
