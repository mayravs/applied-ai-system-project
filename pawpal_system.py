from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


@dataclass
class Pet:
    name: str
    species: str
    age: int
    medications: list[str] = field(default_factory=list)
    tasks: list["Task"] = field(default_factory=list)

    def update_pet_info(self, name: str = None, species: str = None, age: int = None):
        """Update one or more pet fields; omitted fields are left unchanged."""
        if name is not None:
            self.name = name
        if species is not None:
            self.species = species
        if age is not None:
            self.age = age

    def add_task(self, task: "Task"):
        """Append a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task: "Task"):
        """Remove a task from this pet's task list."""
        self.tasks.remove(task)

    def get_pending_tasks(self) -> list["Task"]:
        """Return all tasks that have not yet been marked complete."""
        return [t for t in self.tasks if not t.is_complete]


@dataclass
class Task:
    task_type: str
    description: str
    time: str
    duration: int
    priority: str
    frequency: str          # e.g. "daily", "weekly", "once"
    is_complete: bool = False
    pet: Optional["Pet"] = None
    due_date: date = field(default_factory=date.today)

    @classmethod
    def create_task(cls, task_type: str, duration: int, priority: str, description: str, time: str, frequency: str, pet: Optional["Pet"] = None, due_date: date = None) -> "Task":
        """Named constructor that builds a Task with an optional pet association."""
        kwargs = dict(task_type=task_type, description=description, time=time, duration=duration, priority=priority, frequency=frequency, pet=pet)
        if due_date is not None:
            kwargs["due_date"] = due_date
        return cls(**kwargs)

    def update_task(self, description: str = None, time: str = None, duration: int = None, priority: str = None, frequency: str = None):
        """Update one or more task fields; omitted fields are left unchanged."""
        if description is not None:
            self.description = description
        if time is not None:
            self.time = time
        if duration is not None:
            self.duration = duration
        if priority is not None:
            self.priority = priority
        if frequency is not None:
            self.frequency = frequency

    def mark_complete(self) -> Optional["Task"]:
        """Mark this task done and return the next occurrence for daily/weekly tasks."""
        self.is_complete = True
        if self.frequency == "daily":
            next_due = self.due_date + timedelta(days=1)
        elif self.frequency == "weekly":
            next_due = self.due_date + timedelta(weeks=1)
        else:
            return None
        return Task(
            task_type=self.task_type,
            description=self.description,
            time=self.time,
            duration=self.duration,
            priority=self.priority,
            frequency=self.frequency,
            pet=self.pet,
            due_date=next_due,
        )


class Schedule:
    def __init__(self, pets: list[Pet] = None):
        self.pets: list[Pet] = pets if pets is not None else []

    def add_task(self, pet: Pet, task: Task):
        """Assign a task to a specific pet."""
        pet.add_task(task)

    def remove_task(self, pet: Pet, task: Task):
        """Remove a task from a specific pet."""
        pet.remove_task(task)

    def mark_task_complete(self, pet: Pet, task: Task):
        """Mark a task complete and auto-schedule the next occurrence for daily/weekly tasks."""
        next_task = task.mark_complete()
        if next_task is not None:
            self.add_task(pet, next_task)

    def get_tasks_for_pet(self, pet: Pet) -> list[Task]:
        """Return all tasks belonging to a specific pet."""
        return pet.tasks

    def get_all_pending_tasks(self) -> list[Task]:
        """Return all incomplete tasks across every pet."""
        return [task for pet in self.pets for task in pet.get_pending_tasks()]

    def get_all_completed_tasks(self) -> list[Task]:
        """Return all completed tasks across every pet."""
        return [task for pet in self.pets for task in pet.tasks if task.is_complete]    
    
    def get_tasks_by_time(self, time: str) -> list[Task]:
        """Return all tasks scheduled at a given time across every pet."""
        return [task for pet in self.pets for task in pet.tasks if task.time == time]

    def get_tasks_by_type(self, task_type: str) -> list[Task]:
        """Return all tasks of a given type across every pet."""
        return [task for pet in self.pets for task in pet.tasks if task.task_type == task_type]

    def _to_minutes(self, time_str: str) -> int:
        """Convert a time string in HH:MM format to total minutes since midnight."""
        return int(time_str[:2]) * 60 + int(time_str[3:])

    def get_conflicts(self, due_date: date = None) -> list[str]:
        """Return a warning string for every pair of tasks whose time windows overlap.

        Two tasks conflict when: a_start < b_end AND b_start < a_end.
        This catches both exact same-start and partial duration overlaps.
        Never raises — callers receive an empty list when the schedule is clean.

        If due_date is given, only tasks due on that date are considered — lets a
        "today's plan" view report only today's conflicts instead of ones on other days.
        """
        indexed = [
            (pet, task) for pet in self.pets for task in pet.tasks
            if due_date is None or task.due_date == due_date
        ]
        warnings = []
        for i, (pet_a, task_a) in enumerate(indexed):
            a_start = self._to_minutes(task_a.time)
            a_end = a_start + task_a.duration
            for pet_b, task_b in indexed[i + 1:]:
                if task_a.due_date != task_b.due_date:
                    continue
                b_start = self._to_minutes(task_b.time)
                b_end = b_start + task_b.duration
                if a_start < b_end and b_start < a_end:
                    warnings.append(
                        f"WARNING: {pet_a.name}'s '{task_a.task_type}' "
                        f"({task_a.time}, {task_a.duration} min) overlaps with "
                        f"{pet_b.name}'s '{task_b.task_type}' ({task_b.time}, {task_b.duration} min)"
                    )
        return warnings

    def get_tasks_sorted_by_time(self, due_date: date = None) -> list[Task]:
        """Return tasks across every pet sorted chronologically.

        If due_date is given, only tasks due on that date are included — this is what
        powers "today's plan" so a recurring task's freshly-created next occurrence
        (due tomorrow) doesn't show up alongside the one just marked complete today.
        """
        PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2} # used as a tiebreaker for tasks with the same time
        all_tasks = [
            task for pet in self.pets for task in pet.tasks
            if due_date is None or task.due_date == due_date
        ]
        return sorted(all_tasks,key=lambda t: (int(t.time[:2]) * 60 + int(t.time[3:]), PRIORITY_ORDER.get(t.priority, 99)))

class Owner:
    def __init__(self, name: str, address: str, phone: str):
        self.name = name
        self.address = address
        self.phone = phone
        self.pets: list[Pet] = []
        self.schedule: Schedule = Schedule(pets=self.pets)

    def add_pet(self, pet: Pet):
        """Add a pet to this owner's roster."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet):
        """Remove a pet from this owner's roster."""
        self.pets.remove(pet)

    def find_pet(self, name: str) -> Optional[Pet]:
        """Return the first pet matching the given name, or None if not found."""
        return next((p for p in self.pets if p.name == name), None)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def get_all_pending_tasks(self) -> list[Task]:
        """Return all incomplete tasks across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.get_pending_tasks()]