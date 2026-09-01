from datetime import datetime, timedelta, timezone
import math
import pytest

from goalcoach.domain.retention import calculate_retention, decayed_retention


def test_retention_zero_elapsed_time() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    # When delta_t == 0, R(t) should equal R_0
    assert calculate_retention(
        retention_at_review=0.85, last_reviewed_at=now, at=now
    ) == pytest.approx(0.85)


def test_retention_decay_over_time() -> None:
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=10)
    decay_lambda = 0.05
    expected = 0.9 * math.exp(-0.05 * 10)
    result = calculate_retention(
        retention_at_review=0.9, last_reviewed_at=t0, at=t1, decay_lambda=decay_lambda
    )
    assert result == pytest.approx(expected)
    assert result < 0.9


def test_retention_future_or_negative_elapsed_time_clamped_to_zero_elapsed() -> None:
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    past = t0 - timedelta(days=2)
    # If `at` is before `last_reviewed_at`, elapsed_seconds is clamped to 0.0, so R(t) = R_0
    result = calculate_retention(retention_at_review=0.8, last_reviewed_at=t0, at=past)
    assert result == pytest.approx(0.8)


def test_retention_clamped_between_zero_and_one() -> None:
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=1000)
    # Long time decay approaches 0 but must not go below 0
    result_far = calculate_retention(
        retention_at_review=0.8, last_reviewed_at=t0, at=t1, decay_lambda=0.1
    )
    assert 0.0 <= result_far <= 1.0

    # Upper bound clamping if input R_0 > 1 (e.g. edge float)
    result_upper = calculate_retention(retention_at_review=1.2, last_reviewed_at=t0, at=t0)
    assert result_upper == 1.0


def test_retention_timezone_resilience_naive_and_aware() -> None:
    # Test with both naive datetimes
    naive_t0 = datetime(2026, 9, 1, 12, 0, 0)
    naive_t1 = naive_t0 + timedelta(days=5)
    res1 = calculate_retention(
        retention_at_review=0.9, last_reviewed_at=naive_t0, at=naive_t1, decay_lambda=0.05
    )

    # Test with both aware datetimes in UTC
    utc_t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    utc_t1 = utc_t0 + timedelta(days=5)
    res2 = calculate_retention(
        retention_at_review=0.9, last_reviewed_at=utc_t0, at=utc_t1, decay_lambda=0.05
    )

    # Test with mixed naive last_reviewed_at and aware `at`
    res3 = calculate_retention(
        retention_at_review=0.9, last_reviewed_at=naive_t0, at=utc_t1, decay_lambda=0.05
    )

    # Test with mixed aware last_reviewed_at and naive `at`
    res4 = calculate_retention(
        retention_at_review=0.9, last_reviewed_at=utc_t0, at=naive_t1, decay_lambda=0.05
    )

    expected = 0.9 * math.exp(-0.05 * 5)
    assert res1 == pytest.approx(expected)
    assert res2 == pytest.approx(expected)
    assert res3 == pytest.approx(expected)
    assert res4 == pytest.approx(expected)


def test_retention_default_at_uses_current_time() -> None:
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=2)
    res = calculate_retention(retention_at_review=1.0, last_reviewed_at=past, decay_lambda=0.05)
    expected = 1.0 * math.exp(-0.05 * 2)
    assert res == pytest.approx(expected, rel=1e-2)


def test_retention_invalid_decay_lambda_raises_value_error() -> None:
    now = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="decay_lambda must be strictly positive"):
        calculate_retention(retention_at_review=0.8, last_reviewed_at=now, decay_lambda=0.0)

    with pytest.raises(ValueError, match="decay_lambda must be strictly positive"):
        calculate_retention(retention_at_review=0.8, last_reviewed_at=now, decay_lambda=-0.05)


def test_decayed_retention_helper() -> None:
    t0 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=4)
    # stability_days = 20 -> lambda = 1/20 = 0.05
    res = decayed_retention(
        retention_at_review=0.8, last_reviewed_at=t0, at=t1, stability_days=20.0
    )
    expected = 0.8 * math.exp(-4.0 / 20.0)
    assert res == pytest.approx(expected)

    with pytest.raises(ValueError, match="stability_days must be positive"):
        decayed_retention(retention_at_review=0.8, last_reviewed_at=t0, at=t1, stability_days=0.0)
