# PawPal+

**PawPal+** is a Streamlit-based pet care planner that helps busy owners organize their pet's daily routine by generating an optimized, conflict-checked schedule from task priorities, time constraints, and owner preferences. Its AI-powered extension actively *resolves* scheduling conflicts instead of simply identifying them, then independently validates each proposed solution before applying it to the live schedule, making AI recommendations trustworthy and safe to use.

## Original Project

This project extends **`ai110-module2show-pawpal-starter`** (CodePath AI 110, Module 2 "Show" project): a Streamlit-based pet care planner designed to help busy owners manage their pet's daily routine. Users can add and prioritize care tasks, and the app generates an optimized daily schedule that accounts for available time, preferences, and task importance.

## 🤖 New Feature: AI-Powered Conflict Resolution (Agentic Workflow)

The original scheduler could only *detect* conflicts and print a warning. A human then had to fix them by hand. `ai_scheduler.py` adds an agent that plans, acts, and checks its own work:

1. **Plan** — when `Schedule.get_conflicts()` finds overlaps, the conflicting tasks (and the full task list) are sent to Google's Gemini API (`gemini-flash-latest` via the `google-genai` SDK) with a prompt asking it to propose new start times.
2. **Act** — the proposal is applied to a **deep-copied trial schedule**, never the live one.
3. **Check** — `Schedule.get_conflicts()` (the same deterministic method from the original system) is re-run against the trial schedule. The model's own claim that it "fixed" things is never trusted directly.
4. **Retry or fail safe** — if conflicts remain, the failure is fed back to the model for up to 2 attempts. If it still can't produce a conflict-free proposal, the original schedule is left completely untouched and the caller is told manual review is needed.

### Guardrails

- Gemini is asked for a strict JSON array (`response_mime_type="application/json"`); malformed JSON is rejected, not retried blindly.
- Every proposed change is validated before use: task ids must be in range, times must match `HH:MM` (24-hour). Anything else is silently filtered out.
- Every attempt (accepted or rejected) is logged to `ai_scheduler.log` with a timestamp.
- A missing/invalid `GEMINI_API_KEY` raises a clear `RuntimeError` instead of crashing — both the CLI and the Streamlit app catch it and degrade gracefully (the CLI prints "Skipped: ...", the UI shows an error banner).

## Architecture Overview

Two diagrams live in `diagrams/`:

- **`uml_final.mmd`** — the class diagram (structure): `Owner` owns `Pet`s and a `Schedule`; `Schedule` tracks `Pet`s and queries into their `Task` lists. This is the original system's design, unchanged by the AI addition.
- **`architecture_flow.mmd`** — the data-flow diagram (behavior): CLI (`main.py`) and Streamlit (`app.py`) input both feed the same core scheduling logic, forking at `Schedule.get_conflicts()` — no conflicts goes straight to output; conflicts found hands off to the **Agent** (plan/act loop calling Gemini). Every Agent proposal is checked by an **Evaluator** (`get_conflicts()` re-run on a trial copy) before it can touch the live schedule. Two checkpoints beyond the code itself are shown explicitly: a **human** (CLI runs the Agent automatically, but Streamlit requires a click on "🤖 Resolve conflicts with AI"; a failed resolution says manual review is needed) and a **Tester** (`test_ai_scheduler.py`'s fake-client suite, which verifies the Agent/Evaluator loop offline before it ever hits the real API).

## Getting started

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up your Gemini API key

Required for the AI conflict-resolution feature. Everything else in the app works without it.

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and add your real Gemini API key (get one free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)):

```text
GEMINI_API_KEY=your_real_key_here
```

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

Opens the interactive UI described in [Demo Walkthrough](#demo-walkthrough) below.

### 4. Run the CLI demo

```bash
python3 main.py
```

Runs a hardcoded demo scenario (two pets, several tasks, an intentional conflict) end-to-end and prints the result — see [Sample CLI Output](#-sample-cli-output) below for exactly what this prints.

### 5. Run the tests

```bash
python3 -m pytest
```

Runs all 26 tests (core scheduling logic + AI guardrails) — see [Testing](#-testing) below for the full breakdown.

## 🖥️ Sample CLI Output (with AI resolution)

Running `python3 main.py` prints:
```bash
========================================
  Conflict Report
========================================
  WARNING: Luna's 'exercise' (09:00, 30 min) overlaps with Luna's 'vet' (09:15, 30 min)
  WARNING: Luna's 'exercise' (09:00, 30 min) overlaps with Mochi's 'bath' (09:00, 20 min)
  WARNING: Luna's 'vet' (09:15, 30 min) overlaps with Mochi's 'bath' (09:00, 20 min)
========================================

========================================
  AI Conflict Resolution
========================================
  Moved Luna's vet to 09:30, Mochi's bath to 10:00
========================================

========================================
  Conflict Report
========================================
  No conflicts detected.
========================================

========================================
  Today's Schedule for Alex's Pets
========================================
  [○] 07:00 | Luna | feeding — Morning kibble | 10 min | medium (daily)
  [✓] 08:00 | Mochi | medication — Give Apoquel with food | 5 min | high (daily)
  [✓] 09:00 | Luna | exercise — 30-minute walk | 30 min | high (daily)
  [○] 09:30 | Luna | vet — Annual checkup | 30 min | high (once)
  [○] 10:00 | Mochi | bath — Monthly bath | 20 min | medium (once)
  [○] 13:00 | Mochi | playtime — Interactive toy session | 20 min | low (daily)
  [○] 17:00 | Mochi | grooming — Brush coat | 15 min | low (weekly)
  [○] 18:30 | Luna | feeding — Evening kibble | 10 min | medium (daily)
========================================

========================================
  Pending Tasks for Alex's Pets
========================================
  ○ today 07:00 | Luna | feeding — Morning kibble | priority: medium
  ○ today 18:30 | Luna | feeding — Evening kibble | priority: medium
  ○ today 09:30 | Luna | vet — Annual checkup | priority: high
  ○ tomorrow 09:00 | Luna | exercise — 30-minute walk | priority: high
  ○ today 17:00 | Mochi | grooming — Brush coat | priority: low
  ○ today 13:00 | Mochi | playtime — Interactive toy session | priority: low
  ○ today 10:00 | Mochi | bath — Monthly bath | priority: medium
  ○ tomorrow 08:00 | Mochi | medication — Give Apoquel with food | priority: high
========================================
```
## Sample Interactions
### Consistent behavior across different inputs

To show the whole pipeline behaves consistently against Gemini API, here it is run against three different scenarios back to back. No conflicts, a simple 2-task conflict, and a harder 3-way multi-pet conflict. In every case the same guarantee holds: `get_conflicts()` after resolution is empty, because a proposal is never accepted unless it actually passes that check.

```text
--- Scenario: No conflicts ---
Conflicts before: []
Applied: True
Explanation: No conflicts to resolve.
Conflicts after: []

--- Scenario: Simple 2-task conflict ---
Conflicts before: ["WARNING: Whiskers's 'feeding' (08:00, 10 min) overlaps with Whiskers's 'grooming' (08:05, 15 min)"]
Applied: True
Explanation: Moved Whiskers's grooming to 08:10
Conflicts after: []

--- Scenario: 3-way multi-pet conflict ---
Conflicts before: ["WARNING: Luna's 'exercise' (09:00, 30 min) overlaps with Luna's 'vet' (09:15, 30 min)", "WARNING: Luna's 'exercise' (09:00, 30 min) overlaps with Mochi's 'bath' (09:00, 20 min)", "WARNING: Luna's 'vet' (09:15, 30 min) overlaps with Mochi's 'bath' (09:00, 20 min)"]
Applied: True
Explanation: Moved Luna's vet to 09:30, Mochi's bath to 10:00
Conflicts after: []
```

Note: the *exact* times Gemini picks can vary slightly between runs since it's a live model call. That's expected and fine. What's guaranteed consistent is `Applied: True` and an empty `Conflicts after`, because those come from the deterministic verification step, not from the model.

## Design Decisions

- **Verify-then-apply, not trust-then-apply.** Every proposal runs against a deep-copied trial schedule and must pass `get_conflicts()` again before touching the live one. Costs an extra check + copy per attempt; buys safety against a bad LLM response corrupting real data.
- **Max 2 attempts, then fail safe.** Cheap ceiling on retries. Trade-off: a genuinely hard conflict can exhaust both attempts and fall back to "manual review needed" instead of eventually solving it.

## 🧪 Testing

```bash
python3 -m pytest        # run all tests
pytest --cov             # with coverage
```

```bash
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
collected 26 items

tests/test_ai_scheduler.py .....                                         [ 19%]
tests/test_pawpal.py .....................                               [100%]

============================== 26 passed in 0.56s ===============================
```

**Core scheduling** (`test_pawpal.py`, 21 tests)

| Group | Count | Covers |
|---|---|---|
| Task count | 1 | Adding a task appends to the pet's task list |
| Mark complete | 1 | Marking a task flips its status flag |
| Sorting | 7 | Chronological order, priority tiebreaker, multi-pet, empty/no-task edge cases, `due_date` filtering (2 tests) |
| Recurrence | 5 | Daily/weekly advance, `once` returns `None`, field inheritance, schedule integration |
| Conflict detection | 7 | Same-time/overlap/back-to-back/cross-date edge cases, `due_date` filtering (1 test) |

**AI guardrails** (`test_ai_scheduler.py`, 5 tests, fake Gemini client — no network needed)

- No conflicts → the agent isn't called at all.
- A valid proposal that actually fixes the conflict → applied.
- Malformed JSON → rejected, live schedule untouched.
- Out-of-range task ids / bad time formats → filtered out before use.
- **A proposal that *claims* success but doesn't actually fix the conflict** → caught by re-running `get_conflicts()`, never applied. The one that matters most.

**Guardrail examples** — same conflicting schedule (Luna's exercise vs. Mochi's bath, both `09:00`) fed to a fake Gemini client returning bad responses, real captured output:

| Input (fake Gemini response) | Behavior | Result |
|---|---|---|
| `"not json at all"` (×2 attempts) | JSON parse fails both times, no valid proposal to try | `Applied: False`, live schedule unchanged |
| `[{"id": 1, "new_time": "09:15"}]` then `"...09:20"` — both *still* overlap the 09:00-09:30 exercise window | Applied to a trial copy, `get_conflicts()` re-run, still finds the overlap both times | `Applied: False`, live schedule unchanged — the model's own "success" is never trusted |
| `[{"id": 99, ...}, {"id": 1, "new_time": "25:99"}]` — bad id + invalid time, then a second attempt that still doesn't resolve it | Out-of-range id and malformed time are dropped by validation, leaving nothing usable | `Applied: False`, live schedule unchanged |

## Testing Summary
**What worked:** deterministic core logic, no mocking needed. AI guardrails fully tested without hitting the real API.

**What didn't work:**
- `gemini-2.5-flash` 404'd as deprecated. This was fixed by querying `client.models.list()` and switching to `gemini-flash-latest`.
- The AI's success message was silently discarded by `st.rerun()` firing before Streamlit rendered it. This was fixed via `st.session_state`.

**What I learned:** the real bugs weren't in the scheduling logic (tested from day one), they were in Streamlit's rerun model, which fails silently instead of throwing.

## Demo Walkthrough
### UI Features

The Streamlit app has four sections:

- **Owner** — name, address, phone; updates immediately, no form submit.
- **Your Pets** — table of all pets, plus a form to add one (name, age, species, medications).
- **Tasks** — a **Pet** dropdown picks which pet a new task belongs to, then a form (title, time, due date, duration, frequency, priority, description). Existing tasks are listed below with status and a date label (`today` / `tomorrow` / date); conflicts show inline with a **"🤖 Resolve conflicts with AI"** button.
- **Build Schedule** — today's plan only: conflict banner, summary metrics, progress bar, and each task with an inline **Mark done** button. Stays visible across actions, so marking a task done doesn't hide the plan.

### Example Workflow

1. **Enter owner info** — type a name (e.g., *Jordan*), address, and phone in the Owner section.
2. **Add a pet** — open the *Add a pet* form, enter `Mochi`, species `cat`, age `5`, medications `Apoquel`, and click **Add pet**.
3. **Add tasks** — pick `Mochi` from the **Pet** dropdown, then add `Morning medication` (`08:00`, `5` min, `daily`, `high`).
4. **Introduce a conflict** — add a second task, `Vet visit`, also at `08:00` (30 min). A red warning banner appears: `WARNING: Mochi's 'Morning medication' (08:00, 5 min) overlaps with Mochi's 'Vet visit' (08:00, 30 min)`.
5. **Resolve it with AI** — click **"🤖 Resolve conflicts with AI"**. Gemini proposes a new time, verifies it's actually conflict-free, and the banner clears.
6. **Generate the schedule** — in Build Schedule, click **Generate schedule** to see today's plan: conflict status, summary metrics, and each task in chronological order.
7. **Mark a task done** — click **Mark done** on `Morning medication` right there in the schedule. It strikes through, and (being `daily`) a new occurrence is queued for `tomorrow` (visible back in the Tasks list).

## Reflection

The biggest lesson: don't trust a generative step just because it claims success. Verify with a deterministic, non-AI check that already exists. That plan → act → verify pattern generalizes well beyond this scheduler.