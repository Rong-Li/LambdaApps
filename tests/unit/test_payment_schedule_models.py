"""Tests for PaymentSchedule Pydantic models."""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from service.shared.models import Frequency, PaymentScheduleInput
from service.shared.models.enums import Category, TransactionType


class TestPaymentScheduleInput:
    """Tests for PaymentScheduleInput model validation."""

    def test_valid_weekly_schedule(self):
        """Test creating a valid weekly payment schedule."""
        schedule = PaymentScheduleInput(
            name='Weekly Groceries',
            amount=100.00,
            category=Category.Groceries,
            frequency=Frequency.Weekly,
            start_date=date(2026, 1, 1),
        )

        assert schedule.name == 'Weekly Groceries'
        assert schedule.amount == 100.00
        assert schedule.frequency == Frequency.Weekly
        assert schedule.transaction_type == TransactionType.Debit
        assert schedule.monthly_dates is None

    def test_valid_monthly_schedule_with_dates(self):
        """Test creating a valid monthly payment schedule with specific dates."""
        schedule = PaymentScheduleInput(
            name='Rent Payment',
            amount=1500.00,
            category=Category.Housing,
            frequency=Frequency.Monthly,
            monthly_dates=[1, 15],
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )

        assert schedule.name == 'Rent Payment'
        assert schedule.frequency == Frequency.Monthly
        assert schedule.monthly_dates == [1, 15]
        assert schedule.end_date == datetime(2027, 12, 31, tzinfo=timezone.utc)

    def test_monthly_requires_dates(self):
        """Test that monthly frequency requires monthly_dates."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentScheduleInput(
                name='Missing Dates',
                amount=100.00,
                category=Category.Utilities,
                frequency=Frequency.Monthly,
                start_date=date(2026, 1, 1),
            )

        assert 'monthly_dates is required' in str(exc_info.value)

    def test_non_monthly_rejects_dates(self):
        """Test that non-monthly frequencies reject monthly_dates."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentScheduleInput(
                name='Weekly With Dates',
                amount=100.00,
                category=Category.Groceries,
                frequency=Frequency.Weekly,
                monthly_dates=[1, 15],
                start_date=date(2026, 1, 1),
            )

        assert 'monthly_dates should only be set when frequency is Monthly' in str(exc_info.value)

    def test_monthly_dates_must_be_1_to_28(self):
        """Test that monthly_dates values must be between 1 and 28."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentScheduleInput(
                name='Invalid Dates',
                amount=100.00,
                category=Category.Utilities,
                frequency=Frequency.Monthly,
                monthly_dates=[29],
                start_date=date(2026, 1, 1),
            )

        assert 'monthly_dates must be between 1 and 28' in str(exc_info.value)

    def test_monthly_dates_deduped_and_sorted(self):
        """Test that monthly_dates are deduplicated and sorted."""
        schedule = PaymentScheduleInput(
            name='Sorted Dates',
            amount=100.00,
            category=Category.Utilities,
            frequency=Frequency.Monthly,
            monthly_dates=[15, 1, 15, 8],
            start_date=date(2026, 1, 1),
        )

        assert schedule.monthly_dates == [1, 8, 15]

    def test_end_date_must_be_after_start_date(self):
        """Test that end_date must be on or after start_date."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentScheduleInput(
                name='Bad Dates',
                amount=100.00,
                category=Category.Groceries,
                frequency=Frequency.Weekly,
                start_date=date(2026, 6, 1),
                end_date=date(2026, 1, 1),
            )

        assert 'end_date must be on or after start_date' in str(exc_info.value)

    def test_name_required(self):
        """Test that name is required."""
        with pytest.raises(ValidationError):
            PaymentScheduleInput(
                amount=100.00,
                category=Category.Groceries,
                frequency=Frequency.Weekly,
                start_date=date(2026, 1, 1),
            )

    def test_amount_must_be_positive(self):
        """Test that amount must be positive."""
        with pytest.raises(ValidationError):
            PaymentScheduleInput(
                name='Negative Amount',
                amount=-50.00,
                category=Category.Groceries,
                frequency=Frequency.Weekly,
                start_date=date(2026, 1, 1),
            )


class TestFrequency:
    """Tests for Frequency enum."""

    def test_all_frequencies_exist(self):
        """Test all expected frequencies are defined."""
        assert Frequency.Weekly.value == 'Weekly'
        assert Frequency.Biweekly.value == 'Biweekly'
        assert Frequency.Monthly.value == 'Monthly'
