from pathlib import Path
from pydantic import BaseModel
from collections.abc import Iterator
from typing import Literal

GOLDEN_SET_NAME = "golden_set.jsonl"
GOLDEN_SET_FILE_PATH = Path(__file__).parent / GOLDEN_SET_NAME


class RetrievedDoc(BaseModel):
    id: str
    document: str

class ExpectedClaim(BaseModel):
    claim: str
    mark: Literal["S", "U"]

class GoldenCase(BaseModel):
    question: str
    retrieved_context: list[RetrievedDoc]
    generated_answer: str
    expected_claims: list[ExpectedClaim]


def read_file(file_path) -> Iterator[GoldenCase]:
    with open(file_path, "r", encoding="UTF-8") as file:
        for line in file:
            if line.strip():
                yield GoldenCase.model_validate_json(line)



if __name__ == "__main__":

    for line in read_file(GOLDEN_SET_FILE_PATH):
        question = line.question
        expected_claims = line.expected_claims
        print(question)
        print(len(expected_claims))