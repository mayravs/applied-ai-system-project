import copy
import json
import logging
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pawpal_system import Schedule

load_dotenv()

MODEL = "gemini-flash-latest"
MAX_ATTEMPTS = 2
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

logger = logging.getLogger("ai_scheduler")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler("ai_scheduler.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


def get_client() -> genai.Client:
    """Build a Gemini client from GEMINI_API_KEY, failing loudly if it's missing."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return genai.Client(api_key=api_key)


@dataclass
class ResolutionResult:
    applied: bool
    explanation: str
    conflicts_before: list[str]
    conflicts_after: list[str]


def _flatten(schedule: Schedule) -> list[tuple]:
    return [(pet, task) for pet in schedule.pets for task in pet.tasks]


def _build_prompt(indexed_tasks, conflicts: list[str], feedback: str = "") -> str:
    task_lines = "\n".join(
        f"{i}: pet={pet.name}, type={task.task_type}, time={task.time}, "
        f"duration={task.duration}min, priority={task.priority}, due_date={task.due_date}"
        for i, (pet, task) in enumerate(indexed_tasks)
    )
    feedback_block = (
        f"\nYour last proposal still left these conflicts — try different times:\n{feedback}\n"
        if feedback else ""
    )
    return (
        "You are a scheduling assistant for a pet care app. The following tasks have time conflicts:\n"
        f"{chr(10).join(conflicts)}\n\n"
        "Full task list (index: details):\n"
        f"{task_lines}\n"
        f"{feedback_block}\n"
        "Propose new start times (24-hour HH:MM) for ONLY the tasks that need to move to remove "
        "every conflict. Keep changes minimal, prefer moving the lower-priority task in each conflicting "
        "pair, and keep all times between 06:00 and 22:00. Respond with ONLY a JSON array, no markdown "
        "fences, of objects shaped like: [{\"id\": <task index>, \"new_time\": \"HH:MM\"}]. Omit tasks "
        "that don't need to move."
    )


def _request_proposal(indexed_tasks, conflicts, feedback, client) -> list[dict] | None:
    prompt = _build_prompt(indexed_tasks, conflicts, feedback)
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = response.text
    except Exception as exc:
        logger.warning("Gemini request failed: %s", exc)
        return None

    try:
        proposal = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Gemini returned invalid JSON: %r", raw)
        return None

    if not isinstance(proposal, list):
        logger.warning("Gemini proposal was not a JSON array: %r", proposal)
        return None

    valid = []
    for item in proposal:
        if not isinstance(item, dict):
            continue
        task_id, new_time = item.get("id"), item.get("new_time")
        if not isinstance(task_id, int) or not (0 <= task_id < len(indexed_tasks)):
            continue
        if not isinstance(new_time, str) or not TIME_PATTERN.match(new_time):
            continue
        valid.append({"id": task_id, "new_time": new_time})
    return valid


def resolve_conflicts(schedule: Schedule, client=None) -> ResolutionResult:
    """Ask Gemini to propose new times for conflicting tasks, then verify the proposal
    against Schedule.get_conflicts() before applying it.

    The model's own claim that it "fixed" the schedule is never trusted directly — every
    proposal is applied to a deep-copied trial schedule first and only committed to the
    real schedule if the deterministic conflict detector confirms zero conflicts remain.
    """
    conflicts_before = schedule.get_conflicts()
    if not conflicts_before:
        return ResolutionResult(True, "No conflicts to resolve.", [], [])

    client = client or get_client()
    indexed_tasks = _flatten(schedule)
    feedback = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        proposal = _request_proposal(indexed_tasks, conflicts_before, feedback, client)
        if not proposal:
            logger.info("Attempt %d: no usable proposal from Gemini", attempt)
            continue

        trial_schedule = copy.deepcopy(schedule)
        trial_tasks = _flatten(trial_schedule)
        for change in proposal:
            trial_tasks[change["id"]][1].time = change["new_time"]

        trial_conflicts = trial_schedule.get_conflicts()
        if not trial_conflicts:
            explanation = "Moved " + ", ".join(
                f"{indexed_tasks[c['id']][0].name}'s {indexed_tasks[c['id']][1].task_type} to {c['new_time']}"
                for c in proposal
            )
            for change in proposal:
                indexed_tasks[change["id"]][1].time = change["new_time"]
            logger.info("Attempt %d succeeded: %s", attempt, explanation)
            return ResolutionResult(True, explanation, conflicts_before, [])

        logger.info("Attempt %d: proposal left %d conflict(s), retrying", attempt, len(trial_conflicts))
        feedback = "\n".join(trial_conflicts)

    conflicts_after = schedule.get_conflicts()
    logger.warning("Automatic resolution failed after %d attempts", MAX_ATTEMPTS)
    return ResolutionResult(
        False,
        f"Could not automatically resolve conflicts after {MAX_ATTEMPTS} attempts — manual review needed.",
        conflicts_before,
        conflicts_after,
    )


if __name__ == "__main__":
    from pawpal_system import Owner, Pet, Task

    owner = Owner("Alex", "123 Main St", "555-1234")
    luna = Pet(name="Luna", species="dog", age=3)
    mochi = Pet(name="Mochi", species="cat", age=5)
    owner.add_pet(luna)
    owner.add_pet(mochi)

    owner.schedule.add_task(luna, Task.create_task(
        task_type="exercise", duration=30, priority="high",
        description="30-minute walk", time="09:00", frequency="daily", pet=luna,
    ))
    owner.schedule.add_task(mochi, Task.create_task(
        task_type="bath", duration=20, priority="medium",
        description="Monthly bath", time="09:00", frequency="once", pet=mochi,
    ))

    print("Before:", owner.schedule.get_conflicts())
    result = resolve_conflicts(owner.schedule)
    print("Applied:", result.applied)
    print("Explanation:", result.explanation)
    print("After:", owner.schedule.get_conflicts())
