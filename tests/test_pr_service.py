from app.services.pr_service import (
    is_personal_record,
    lift_standing,
    overall_standing,
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


def test_relative_score_favours_a_lighter_or_taller_lifter():
    same_bar = 100
    lighter = relative_score(same_bar, 60, 175)
    heavier = relative_score(same_bar, 70, 175)
    taller = relative_score(same_bar, 70, 190)
    shorter = relative_score(same_bar, 70, 160)
    assert lighter > heavier
    assert taller > shorter


def test_lift_standing_puts_the_heavier_lifter_first():
    board = {1: 100.0, 2: 80.0, 3: 100.0}
    assert lift_standing(100, 1, board) == (1, 3, 100)
    assert lift_standing(80, 2, board) == (3, 3, 0)
    assert lift_standing(90, 4, board) == (3, 4, 33)


def test_overall_standing_is_empty_without_records():
    assert overall_standing(1, [], {}) == (None, 0, None)


def test_overall_standing_averages_each_lift():
    boards = {"Bench press": {1: 100.0, 2: 60.0}, "Squat": {1: 140.0, 2: 100.0}}
    rank, lifters, percentile = overall_standing(1, [("Bench press", 100), ("Squat", 140)], boards)
    assert (rank, lifters, percentile) == (1, 2, 100)
    rank, lifters, percentile = overall_standing(2, [("Bench press", 60), ("Squat", 100)], boards)
    assert (rank, lifters, percentile) == (2, 2, 0)
