import json
from pathlib import Path


CURRENT = Path(__file__).parent / "current.json"
BASELINE = Path(__file__).parent / "baseline.json"

def load(file_path: Path):

    with open(file_path, "r", encoding="UTF-8") as file:
        content = json.load(file)
        return content

def index_by_id(file_path) -> dict:
    indexed = {}
    for entry in file_path:
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
            delta = new_score - old_score
            results.append({"ID": old_id, "old_score": old_score, "new_score": new_score, "delta": delta})
    return results

if __name__ == "__main__":

    current = load(CURRENT)
    print(current)

    indexed_by_id = index_by_id(current)
    print(indexed_by_id)

    baseline = load(BASELINE)


    print(compare(baseline, indexed_by_id))



