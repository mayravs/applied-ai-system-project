from datetime import date, timedelta

from pawpal_system import Owner, Pet, Task
from ai_scheduler import resolve_conflicts


def _date_label(due_date: date) -> str:
    today = date.today()
    if due_date == today:
        return "today"
    if due_date == today + timedelta(days=1):
        return "tomorrow"
    return str(due_date)


def print_schedule(owner: Owner):
    print(f"\n{'='*40}")
    print(f"  Today's Schedule for {owner.name}'s Pets")
    print(f"{'='*40}")

    tasks = owner.schedule.get_tasks_sorted_by_time(due_date=date.today())

    if not tasks:
        print("  No tasks scheduled for today.")
    else:
        for task in tasks:
            status = "✓" if task.is_complete else "○"
            pet_name = task.pet.name if task.pet else "Unknown"
            print(f"  [{status}] {task.time} | {pet_name} | {task.task_type} — {task.description} | {task.duration} min | {task.priority} ({task.frequency})")

    print(f"{'='*40}\n")


def print_conflicts(owner: Owner):
    print(f"{'='*40}")
    print(f"  Conflict Report")
    print(f"{'='*40}")
    conflicts = owner.schedule.get_conflicts()
    if not conflicts:
        print("  No conflicts detected.")
    else:
        for warning in conflicts:
            print(f"  {warning}")
    print(f"{'='*40}\n")


def resolve_conflicts_with_ai(owner: Owner):
    print(f"{'='*40}")
    print(f"  AI Conflict Resolution")
    print(f"{'='*40}")
    try:
        result = resolve_conflicts(owner.schedule)
    except RuntimeError as exc:
        print(f"  Skipped: {exc}")
        print(f"{'='*40}\n")
        return
    print(f"  {result.explanation}")
    print(f"{'='*40}\n")


def print_pending(owner: Owner):
    print(f"{'='*40}")
    print(f"  Pending Tasks for {owner.name}'s Pets")
    print(f"{'='*40}")

    pending = owner.schedule.get_all_pending_tasks()

    if not pending:
        print("  All tasks complete!")
    else:
        for task in pending:
            pet_name = task.pet.name if task.pet else "Unknown"
            print(f"  ○ {_date_label(task.due_date)} {task.time} | {pet_name} | {task.task_type} — {task.description} | priority: {task.priority}")

    print(f"{'='*40}\n")


if __name__ == "__main__":
    owner = Owner("Alex", "123 Main St", "555-1234")

    luna = Pet(name="Luna", species="dog", age=3)
    mochi = Pet(name="Mochi", species="cat", age=5, medications=["Apoquel"])

    owner.add_pet(luna)
    owner.add_pet(mochi)

    # Tasks added out of order intentionally to verify sort works
    owner.schedule.add_task(mochi, Task.create_task(
        task_type="grooming",
        duration=15,
        priority="low",
        description="Brush coat",
        time="17:00",
        frequency="weekly",
        pet=mochi
    ))

    owner.schedule.add_task(luna, Task.create_task(
        task_type="exercise",
        duration=30,
        priority="high",
        description="30-minute walk",
        time="09:00",
        frequency="daily",
        pet=luna
    ))

    owner.schedule.add_task(mochi, Task.create_task(
        task_type="medication",
        duration=5,
        priority="high",
        description="Give Apoquel with food",
        time="08:00",
        frequency="daily",
        pet=mochi
    ))

    owner.schedule.add_task(luna, Task.create_task(
        task_type="feeding",
        duration=10,
        priority="medium",
        description="Morning kibble",
        time="07:00",
        frequency="daily",
        pet=luna
    ))

    owner.schedule.add_task(luna, Task.create_task(
        task_type="feeding",
        duration=10,
        priority="medium",
        description="Evening kibble",
        time="18:30",
        frequency="daily",
        pet=luna
    ))

    owner.schedule.add_task(mochi, Task.create_task(
        task_type="playtime",
        duration=20,
        priority="low",
        description="Interactive toy session",
        time="13:00",
        frequency="daily",
        pet=mochi
    ))

    # Conflicting tasks added intentionally to exercise conflict detection
    owner.schedule.add_task(mochi, Task.create_task(
        task_type="bath",
        duration=20,
        priority="medium",
        description="Monthly bath",
        time="09:00",   # exact same start as Luna's exercise → same-start conflict
        frequency="once",
        pet=mochi
    ))

    owner.schedule.add_task(luna, Task.create_task(
        task_type="vet",
        duration=30,
        priority="high",
        description="Annual checkup",
        time="09:15",   # Luna's exercise runs 09:00–09:30 → duration overlap
        frequency="once",
        pet=luna
    ))

    # Mark recurring tasks complete — next occurrence is auto-scheduled via timedelta
    owner.schedule.mark_task_complete(luna, luna.tasks[0])   # exercise 09:00 → next due tomorrow
    owner.schedule.mark_task_complete(mochi, mochi.tasks[1]) # medication 08:00 → next due tomorrow

    print_conflicts(owner)
    resolve_conflicts_with_ai(owner)
    print_conflicts(owner)
    print_schedule(owner)
    print_pending(owner)