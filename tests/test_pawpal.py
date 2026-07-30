from datetime import date, timedelta
import pytest
from pawpal_system import Owner, Pet, Schedule, Task


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Luna", species="dog", age=3)
    task = Task.create_task(
        task_type="exercise",
        description="30-minute walk",
        duration=30,
        priority="high",
        time="09:00",
        frequency="daily",
        pet=pet
    )

    assert len(pet.tasks) == 0

    pet.add_task(task)

    assert len(pet.tasks) == 1


def test_mark_complete_changes_status():
    task = Task.create_task(
        task_type="feeding",
        duration=10,
        priority="medium",
        description="Morning kibble",
        time="07:00",
        frequency="daily"
    )

    assert task.is_complete is False

    task.mark_complete()

    assert task.is_complete is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_task(time="09:00", priority="medium", frequency="daily", duration=30,
              task_type="walk", due_date=None):
    kwargs = dict(task_type=task_type, description="test task", time=time,
                  duration=duration, priority=priority, frequency=frequency)
    if due_date is not None:
        kwargs["due_date"] = due_date
    return Task.create_task(**kwargs)


def make_schedule(*pets):
    return Schedule(pets=list(pets))


# ---------------------------------------------------------------------------
# Sorting correctness
# ---------------------------------------------------------------------------

def test_sorted_tasks_are_in_chronological_order():
    pet = Pet(name="Luna", species="dog", age=3)
    pet.add_task(make_task(time="14:00"))
    pet.add_task(make_task(time="07:00"))
    pet.add_task(make_task(time="11:30"))

    schedule = make_schedule(pet)
    sorted_tasks = schedule.get_tasks_sorted_by_time()

    times = [t.time for t in sorted_tasks]
    assert times == sorted(times), f"Expected chronological order, got {times}"


def test_same_time_sorted_by_priority():
    pet = Pet(name="Mochi", species="cat", age=2)
    pet.add_task(make_task(time="08:00", priority="low"))
    pet.add_task(make_task(time="08:00", priority="high"))
    pet.add_task(make_task(time="08:00", priority="medium"))

    schedule = make_schedule(pet)
    priorities = [t.priority for t in schedule.get_tasks_sorted_by_time()]

    assert priorities == ["high", "medium", "low"]


def test_sort_tasks_across_multiple_pets():
    dog = Pet(name="Rex", species="dog", age=5)
    cat = Pet(name="Whiskers", species="cat", age=3)
    dog.add_task(make_task(time="10:00", task_type="walk"))
    cat.add_task(make_task(time="08:00", task_type="feeding"))

    schedule = make_schedule(dog, cat)
    times = [t.time for t in schedule.get_tasks_sorted_by_time()]

    assert times == ["08:00", "10:00"]


def test_sort_empty_schedule_returns_empty_list():
    schedule = make_schedule()
    assert schedule.get_tasks_sorted_by_time() == []


def test_sort_pet_with_no_tasks():
    pet = Pet(name="Goldie", species="fish", age=1)
    schedule = make_schedule(pet)
    assert schedule.get_tasks_sorted_by_time() == []


def test_due_date_filter_excludes_tasks_on_other_dates():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    pet = Pet(name="Luna", species="dog", age=3)
    pet.add_task(make_task(time="09:00", due_date=today, task_type="exercise"))
    pet.add_task(make_task(time="09:00", due_date=tomorrow, task_type="exercise"))

    schedule = make_schedule(pet)
    todays_tasks = schedule.get_tasks_sorted_by_time(due_date=today)

    assert len(todays_tasks) == 1
    assert todays_tasks[0].due_date == today


def test_no_due_date_filter_returns_tasks_from_every_date():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    pet = Pet(name="Luna", species="dog", age=3)
    pet.add_task(make_task(time="09:00", due_date=today))
    pet.add_task(make_task(time="10:00", due_date=tomorrow))

    schedule = make_schedule(pet)
    assert len(schedule.get_tasks_sorted_by_time()) == 2


# ---------------------------------------------------------------------------
# Recurrence logic
# ---------------------------------------------------------------------------

def test_daily_task_creates_next_day_task():
    today = date.today()
    task = make_task(frequency="daily", due_date=today)

    next_task = task.mark_complete()

    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)


def test_weekly_task_creates_task_one_week_later():
    today = date.today()
    task = make_task(frequency="weekly", due_date=today)

    next_task = task.mark_complete()

    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_once_task_returns_none():
    task = make_task(frequency="once")
    next_task = task.mark_complete()
    assert next_task is None


def test_recurring_task_inherits_all_fields():
    today = date.today()
    pet = Pet(name="Luna", species="dog", age=3)
    task = Task.create_task(
        task_type="medication",
        description="Evening pill",
        time="18:00",
        duration=5,
        priority="high",
        frequency="daily",
        pet=pet,
        due_date=today,
    )

    next_task = task.mark_complete()

    assert next_task.task_type == task.task_type
    assert next_task.description == task.description
    assert next_task.time == task.time
    assert next_task.duration == task.duration
    assert next_task.priority == task.priority
    assert next_task.frequency == task.frequency
    assert next_task.pet is pet


def test_schedule_mark_complete_adds_next_task_to_pet():
    pet = Pet(name="Biscuit", species="dog", age=4)
    task = make_task(frequency="daily")
    pet.add_task(task)

    schedule = make_schedule(pet)
    schedule.mark_task_complete(pet, task)

    assert len(pet.tasks) == 2
    assert pet.tasks[0].is_complete is True
    assert pet.tasks[1].is_complete is False


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_exact_same_time_flags_conflict():
    today = date.today()
    pet = Pet(name="Rex", species="dog", age=2)
    pet.add_task(make_task(time="09:00", duration=30, due_date=today, task_type="walk"))
    pet.add_task(make_task(time="09:00", duration=30, due_date=today, task_type="bath"))

    schedule = make_schedule(pet)
    assert len(schedule.get_conflicts()) == 1


def test_overlapping_tasks_flag_conflict():
    today = date.today()
    pet = Pet(name="Noodle", species="cat", age=1)
    pet.add_task(make_task(time="09:00", duration=30, due_date=today, task_type="grooming"))
    pet.add_task(make_task(time="09:20", duration=30, due_date=today, task_type="vet"))

    schedule = make_schedule(pet)
    assert len(schedule.get_conflicts()) >= 1


def test_back_to_back_tasks_no_conflict():
    today = date.today()
    pet = Pet(name="Pretzel", species="dog", age=6)
    pet.add_task(make_task(time="09:00", duration=30, due_date=today, task_type="walk"))
    pet.add_task(make_task(time="09:30", duration=30, due_date=today, task_type="feeding"))

    schedule = make_schedule(pet)
    assert schedule.get_conflicts() == []


def test_same_time_different_dates_no_conflict():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    pet = Pet(name="Kiwi", species="bird", age=2)
    pet.add_task(make_task(time="10:00", duration=30, due_date=today, task_type="feeding"))
    pet.add_task(make_task(time="10:00", duration=30, due_date=tomorrow, task_type="feeding"))

    schedule = make_schedule(pet)
    assert schedule.get_conflicts() == []


def test_no_conflicts_in_empty_schedule():
    schedule = make_schedule()
    assert schedule.get_conflicts() == []


def test_no_conflicts_with_single_task():
    today = date.today()
    pet = Pet(name="Pip", species="hamster", age=1)
    pet.add_task(make_task(time="08:00", duration=15, due_date=today))

    schedule = make_schedule(pet)
    assert schedule.get_conflicts() == []


def test_due_date_filter_hides_conflicts_on_other_days():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    pet = Pet(name="Rex", species="dog", age=2)
    pet.add_task(make_task(time="09:00", duration=30, due_date=tomorrow, task_type="walk"))
    pet.add_task(make_task(time="09:00", duration=30, due_date=tomorrow, task_type="bath"))

    schedule = make_schedule(pet)

    assert schedule.get_conflicts(due_date=today) == []
    assert len(schedule.get_conflicts(due_date=tomorrow)) == 1
    assert len(schedule.get_conflicts()) == 1