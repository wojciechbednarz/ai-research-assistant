import json
from pathlib import Path
from pprint import pprint
import sys


def load(file_path: Path):

    with open(file_path, "r", encoding="UTF-8") as file:
        content = json.load(file)
        return content

def index_by_id(rows) -> dict:
    indexed = {}
    for entry in rows:
        indexed[entry["id"]] = entry["score"]
    return indexed

def compare(baseline_rows, current_index):

    results = []
    for row in baseline_rows:
        old_id, old_score = row["id"], row["score"]
        new_score = current_index.get(old_id)
        if new_score is None:
            results.append({"ID": old_id, "status": "missing"})
        else:
            delta = round(new_score - old_score, 2)
            results.append({"ID": old_id, "old_score": old_score, "new_score": new_score, "delta": delta})
    return results

def find_regressions(rows: list) -> dict:
    regressions = {}
    for row in rows:
        status = row.get("status")
        delta = row.get("delta")
        if status == "missing":
            regressions[row["ID"]] = status 
        if delta and delta < 0:
            regressions[row["ID"]] = delta
    return regressions

if __name__ == "__main__":


    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} BASELINE CURRENT")

    baseline_path = Path(sys.argv[1])
    current_path = Path(sys.argv[2])

    baseline = load(baseline_path)

    current = load(current_path)
    current_indexed_by_id = index_by_id(current)

    comparison = compare(baseline, current_indexed_by_id)
    pprint(comparison)

    regressions = find_regressions(comparison)
    if regressions:
        sys.exit(f"Wrong: {regressions}")
