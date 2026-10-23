import pytest
from app.services.pr_service import (
    estimated_one_rep_max,
    is_personal_record,
    personal_record_indexes,
    relative_score,
)


def test_first_lift_is_a_personal_record():
    assert is_personal_record(60, None) is True


def test_heavier_than_history_is_a_personal_record():
    assert is_personal_record(100, 80) is True
    assert is_personal_record(80, 80) is False
    assert is_personal_record(70, 80) is False


def test_each_new_high_in_a_session_is_flagged():
    assert personal_record_indexes([80, 90, 85, 100], None) == [0, 1, 3]


def test_session_compares_against_previous_best():
    assert personal_record_indexes([90, 110, 105], 100) == [1]


def test_a_single_is_its_own_max():
    assert estimated_one_rep_max(140, 1) == 140


def test_reps_raise_the_estimate():
    assert estimated_one_rep_max(100, 5) == pytest.approx(116.67, abs=0.01)
    assert estimated_one_rep_max(100, 10) > estimated_one_rep_max(120, 1)


def test_relative_score_favours_the_lighter_lifter():
    assert relative_score(120, 60) > relative_score(120, 80)
