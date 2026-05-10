from app.services import scheduler


def test_cron_for_cycle_off_and_on_demand_have_no_trigger():
    assert scheduler._cron_for_cycle("off") is None
    assert scheduler._cron_for_cycle("on_demand") is None


def test_cron_for_cycle_returns_trigger_for_cron_cycles():
    for cycle in ("hourly", "every_4h", "daily"):
        assert scheduler._cron_for_cycle(cycle) is not None


def test_schedule_and_unschedule_no_op_without_start():
    """Service hooks call into scheduler module functions; before start they
    must be safe no-ops."""
    from datetime import datetime, timezone
    from decimal import Decimal

    from app.models.agent import Agent

    a = Agent(
        id=1,
        subject_id=1,
        role_id=1,
        display_name="x",
        system_prompt="",
        model="m",
        cycle="hourly",
        daily_budget_usd=Decimal("1"),
        spent_today_usd=Decimal("0"),
        created_at=datetime.now(timezone.utc),
    )
    # No exceptions:
    scheduler.schedule_agent(a)
    scheduler.unschedule_agent(99)
