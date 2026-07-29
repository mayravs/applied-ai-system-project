# PawPal+ 

## Original System's Goals & Capabilities

**PawPal+** is a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

## Capabilities

- User can enter basic owner + pet info
- User can add/edit tasks (duration + priority at minimum)
- Generates a daily schedule/plan based on constraints and priorities
- Displays the plan clearly (and ideally explain the reasoning)
- Includes tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Set up your Gemini API key

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```text
GEMINI_API_KEY=your_real_key_here
```

### Run the app

```bash
streamlit run app.py
```

## 🖥️ Sample CLI Output
```bash
========================================
  Conflict Report
========================================
  WARNING: Luna's 'exercise' (09:00, 30 min) overlaps with Luna's 'vet' (09:15, 30 min)
  WARNING: Luna's 'exercise' (09:00, 30 min) overlaps with Mochi's 'bath' (09:00, 20 min)
  WARNING: Luna's 'vet' (09:15, 30 min) overlaps with Mochi's 'bath' (09:00, 20 min)
========================================

========================================
  Today's Schedule for Alex's Pets
========================================
  [○] 2026-07-05 07:00 | Luna | feeding — Morning kibble | 10 min | medium (daily)
  [✓] 2026-07-05 08:00 | Mochi | medication — Give Apoquel with food | 5 min | high (daily)
  [○] 2026-07-06 08:00 | Mochi | medication — Give Apoquel with food | 5 min | high (daily)
  [✓] 2026-07-05 09:00 | Luna | exercise — 30-minute walk | 30 min | high (daily)
  [○] 2026-07-06 09:00 | Luna | exercise — 30-minute walk | 30 min | high (daily)
  [○] 2026-07-05 09:00 | Mochi | bath — Monthly bath | 20 min | medium (once)
  [○] 2026-07-05 09:15 | Luna | vet — Annual checkup | 30 min | high (once)
  [○] 2026-07-05 13:00 | Mochi | playtime — Interactive toy session | 20 min | low (daily)
  [○] 2026-07-05 17:00 | Mochi | grooming — Brush coat | 15 min | low (weekly)
  [○] 2026-07-05 18:30 | Luna | feeding — Evening kibble | 10 min | medium (daily)
========================================

========================================
  Pending Tasks for Alex's Pets
========================================
  ○ 07:00 | Luna | feeding — Morning kibble | priority: medium
  ○ 18:30 | Luna | feeding — Evening kibble | priority: medium
  ○ 09:15 | Luna | vet — Annual checkup | priority: high
  ○ 09:00 | Luna | exercise — 30-minute walk | priority: high
  ○ 17:00 | Mochi | grooming — Brush coat | priority: low
  ○ 13:00 | Mochi | playtime — Interactive toy session | priority: low
  ○ 09:00 | Mochi | bath — Monthly bath | priority: medium
  ○ 08:00 | Mochi | medication — Give Apoquel with food | priority: high
========================================
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
python3 -m pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```bash
============================================================================ test session starts =============================================================================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/mayra/Github/ai110-module2show-pawpal-starter
plugins: anyio-4.14.0
collected 18 items                                                                                                                                                           

tests/test_pawpal.py ..................                                                                                                                                [100%]

============================================================================= 18 passed in 0.02s =============================================================================
```

**Confidence Level:** ⭐⭐⭐⭐

Tests Summary:

Task Count (1 test)
- Happy path: adding a task appends to the pet's task list

Mark Complete (1 test)
- Happy path: marking a task complete flips the status flag on a task

Sorting (5 tests)
- Happy path: 3 tasks in random order → returned chronologically
- Tiebreaker: same time, priority order (high → medium → low)
- Multi-pet: tasks from different pets interleave by time
- Edge cases: empty schedule and a pet with no tasks both return []

Recurrence (5 tests)
- Happy paths: daily advances by 1 day, weekly advances by 7 days
- Edge case: once frequency returns None (no follow-up)
- Field inheritance: the new task copies all fields including the pet reference
- Integration: schedule.mark_task_complete() leaves the pet with 2 tasks (1 done, 1 pending)

Conflict detection (6 tests)
- Happy paths: exact same time flags a conflict, partial overlap flags a conflict
- Edge cases: back-to-back tasks (touching but not overlapping) → no conflict; same time on different dates → no conflict; empty schedule and single task → no conflict

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Schedule.get_tasks_sorted_by_time()` | Primary sort by start time (converted to minutes); priority as tiebreaker within the same slot. |
| Filtering | `Schedule.get_all_pending_tasks()`, `Schedule.get_all_completed_tasks()`, `Schedule.get_tasks_by_time(time)`, `Schedule.get_tasks_by_type(task_type)` | Filters on `is_complete`, exact time match, or task type across all pets. |
| Conflict detection | `Schedule.get_conflicts()` | Interval overlap check (`a_start < b_end AND b_start < a_end`); scoped to same `due_date` to avoid cross-day false positives. Returns warning strings, never raises. |
| Recurring tasks | `Task.mark_complete()`, `Schedule.mark_task_complete(pet, task)` | `mark_complete()` returns the next `Task` using `timedelta`; `mark_task_complete()` appends it to the pet automatically. `"once"` tasks return `None`. |

## Demo Walkthrough

### UI Features

The Streamlit app is divided into four sections, each visible on a single scrollable page:

- **Owner** — three text inputs for name, address, and phone. Changes apply immediately without a form submit.
- **Your Pets** — a table listing every pet (name, species, age, medications). Below it, a form lets you add a new pet with a name, age, species dropdown, and an optional comma-separated medications field.
- **Tasks** — inputs for task title, time (HH:MM), duration (minutes), frequency (`daily` / `weekly` / `once`), priority (`low` / `medium` / `high`), and an optional description. Each existing task shows its status (⏳ pending or ✅ done) and a **Mark done** button. Conflict warnings appear inline as red banners immediately after tasks are added.
- **Build Schedule** — a single button that renders a conflict-status banner, three summary metrics (total / pending / completed), a progress bar, and a sortable dataframe of all tasks in chronological order.

### Example Workflow

1. **Enter owner info** — type a name (e.g., *Jordan*), address, and phone in the Owner section.
2. **Add a pet** — open the *Add a pet* form, enter `Mochi`, species `cat`, age `5`, medications `Apoquel`, and click **Add pet**. The pets table updates immediately.
3. **Add tasks** — set task title to `Morning medication`, time `08:00`, duration `5`, frequency `daily`, priority `high`, then click **Add task**. Repeat for any other tasks (e.g., a `Playtime` task at `13:00`).
4. **Introduce a conflict** — add a second task starting at `08:00` (e.g., a `Vet visit` of 30 min). A red warning banner appears: `WARNING: Mochi's 'Morning medication' (08:00, 5 min) overlaps with Mochi's 'Vet visit' (08:00, 30 min)`.
5. **Mark a task done** — click **Mark done** on `Morning medication`. The task strikes through, its status flips to ✅, and a new pending occurrence is automatically queued for the next day.
6. **Generate the schedule** — click **Generate schedule** to see all tasks sorted chronologically, the conflict banner, and live pending/completed counts.

### Key Scheduler Behaviors

| Behavior | What you see |
|---|---|
| **Chronological sort** | Tasks always appear earliest-first regardless of the order they were added. |
| **Priority tiebreaker** | Two tasks at the same time are ordered high → medium → low. |
| **Conflict detection** | Any two tasks whose time windows overlap on the same date trigger a red `WARNING:` banner. Back-to-back tasks (one ends exactly when the next begins) do not conflict. |
| **Recurring auto-schedule** | Marking a `daily` task done creates a copy due tomorrow; `weekly` tasks advance by 7 days; `once` tasks do not recur. |
| **Cross-pet view** | The schedule and conflict check span all pets — Luna's 09:00 walk can conflict with Mochi's 09:00 bath. |