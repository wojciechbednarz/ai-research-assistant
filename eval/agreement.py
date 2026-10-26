from pathlib import Path
from dataclasses import dataclass
import json

BASELINE = "baseline.json"
BASELINE_FILE_PATH = Path(__file__).parent / BASELINE
DECIMAL = 9

@dataclass
class EvalData:
    question: str
    id: str
    expected: float
    score: float



def load_rows(path: Path) -> list[EvalData]:
    # instead i guess we could also import eval/compare.py:7 (load())
    eval_list = []
    with open(path, "r", encoding="UTF-8") as file:
        content = json.load(file)
        for entry in content:
            eval_list.append(EvalData(
                question=entry["question"],
                id=entry["id"],
                expected=entry["expected"],
                score=entry["score"]
            ))
        return eval_list

def row_agrees(expected: float, score: float, tol: float) -> bool:
    return round(abs(expected - score), DECIMAL) <= tol

def calc_mean_average_error(rows: list[EvalData]) -> float:
    # MAE = ( |e₁ − s₁| + |e₂ − s₂| + … + |eₙ − sₙ| ) / n
    if not rows:
        raise ValueError(f"Rows are empty: {len(rows)}")
    mae = 0.0
    for entry in rows:
        mae += abs(entry.expected - entry.score)
    total_mae = mae / len(rows)
    return total_mae


def summarise(rows: list[EvalData], tol: float) -> dict:
    # agree - count, total - int, mae - float, disagreements - list
    agree = 0
    disagreements = []
    for row in rows:
        agree_eval = row_agrees(row.expected, row.score, tol)
        if agree_eval:
            agree += 1
        else:
            disagreements.append(row.id)
    mae = calc_mean_average_error(rows)
    return {
        "agree": agree,
        "total": len(rows),
        "mae": mae,
        "disagreements": disagreements
    }

if __name__ == "__main__":
    tol = 0.1
    rows = load_rows(BASELINE_FILE_PATH)
    print(summarise(rows, tol))
