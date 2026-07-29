import pytest
from pawpal_system import Owner, Pet, Task
from ai_scheduler import resolve_conflicts


# ---------------------------------------------------------------------------
# Fake Gemini client — lets us test the guardrail logic without network calls
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        if self.calls > len(self._responses):
            raise AssertionError("FakeClient received more calls than expected")
        return FakeResponse(self._responses[self.calls - 1])


class FakeClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)


def make_conflicting_schedule():
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
    return owner.schedule


# ---------------------------------------------------------------------------
# No-op path
# ---------------------------------------------------------------------------

def test_no_conflicts_short_circuits_without_calling_gemini():
    owner = Owner("Alex", "123 Main St", "555-1234")
    luna = Pet(name="Luna", species="dog", age=3)
    owner.add_pet(luna)
    owner.schedule.add_task(luna, Task.create_task(
        task_type="exercise", duration=30, priority="high",
        description="walk", time="09:00", frequency="daily", pet=luna,
    ))

    client = FakeClient(responses=[])
    result = resolve_conflicts(owner.schedule, client=client)

    assert result.applied is True
    assert result.conflicts_before == []
    assert client.models.calls == 0


# ---------------------------------------------------------------------------
# Happy path — valid proposal that actually resolves the conflict
# ---------------------------------------------------------------------------

def test_valid_proposal_is_applied_and_conflict_disappears():
    schedule = make_conflicting_schedule()
    client = FakeClient(responses=['[{"id": 1, "new_time": "09:30"}]'])

    result = resolve_conflicts(schedule, client=client)

    assert result.applied is True
    assert result.conflicts_after == []
    assert schedule.get_conflicts() == []
    bath = next(t for pet in schedule.pets for t in pet.tasks if t.task_type == "bath")
    assert bath.time == "09:30"


# ---------------------------------------------------------------------------
# Guardrail — malformed JSON must never be trusted or applied
# ---------------------------------------------------------------------------

def test_invalid_json_is_rejected_and_schedule_is_untouched():
    schedule = make_conflicting_schedule()
    original_times = [t.time for pet in schedule.pets for t in pet.tasks]
    client = FakeClient(responses=["not json at all", "still not json"])

    result = resolve_conflicts(schedule, client=client)

    assert result.applied is False
    assert result.conflicts_after != []
    assert [t.time for pet in schedule.pets for t in pet.tasks] == original_times


# ---------------------------------------------------------------------------
# Guardrail — a proposal that claims success but doesn't actually fix anything
# must be caught by re-running get_conflicts(), not trusted at face value.
# ---------------------------------------------------------------------------

def test_proposal_that_does_not_resolve_conflict_is_not_applied():
    schedule = make_conflicting_schedule()
    original_times = [t.time for pet in schedule.pets for t in pet.tasks]
    # Moves the bath to 09:15, which still overlaps the 09:00-09:30 exercise window.
    client = FakeClient(responses=[
        '[{"id": 1, "new_time": "09:15"}]',
        '[{"id": 1, "new_time": "09:20"}]',
    ])

    result = resolve_conflicts(schedule, client=client)

    assert result.applied is False
    assert result.conflicts_after != []
    assert [t.time for pet in schedule.pets for t in pet.tasks] == original_times
    assert client.models.calls == 2


# ---------------------------------------------------------------------------
# Guardrail — out-of-range ids and bad time formats are filtered out, not applied
# ---------------------------------------------------------------------------

def test_out_of_range_id_and_bad_time_format_are_filtered():
    schedule = make_conflicting_schedule()
    original_times = [t.time for pet in schedule.pets for t in pet.tasks]
    client = FakeClient(responses=[
        '[{"id": 99, "new_time": "09:30"}, {"id": 1, "new_time": "25:99"}]',
        '[{"id": 1, "new_time": "09:15"}]',
    ])

    result = resolve_conflicts(schedule, client=client)

    assert result.applied is False
    assert [t.time for pet in schedule.pets for t in pet.tasks] == original_times
