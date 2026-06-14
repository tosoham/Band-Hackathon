import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class QuestionRow:
    question_id: str
    category: str
    question: str


def load_questions(path: str) -> list[QuestionRow]:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            QuestionRow(
                question_id=row["question_id"],
                category=row["category"],
                question=row["question"],
            )
            for row in reader
        ]
