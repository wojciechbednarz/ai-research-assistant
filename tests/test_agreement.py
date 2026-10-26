from eval.agreement import row_agrees
import pytest



@pytest.mark.parametrize(
    "expected, score, tol, outcome",
    [
        (0.4, 0.3, 0.1, True),
        (0.4, 0.3, 0.05, False),
        (0.4, 0.4, 0.0, True),
        (0.333, 0.5, 0.1, False)
    ]
    
)
def test_row_agrees(expected, score, tol, outcome):
    assert row_agrees(expected, score, tol) == outcome

