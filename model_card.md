# Model Card — Responsible AI Reflection

## How I Collaborated with AI

I used Claude Code conversationally rather than handing it one big spec: picked the AI feature (agentic conflict resolution) from a short list of trade-offs it laid out, then built it in small steps. Starting with an API key setup, then the core `resolve_conflicts()` loop, then tests, then wiring it into `main.py`/`app.py`. Lastly, a round of UI fixes based on things I noticed while actually using the app. Most changes were verified in a real running instance (CLI output) before being called done, not just by reading the diff.

## One Helpful AI Suggestion

When I asked for the AI feature to use Gemini, the first model name it tried (`gemini-2.5-flash`) 404'd as deprecated. Rather than guessing another hardcoded name, it queried `client.models.list()` against my real API key to see what was actually available, and picked `gemini-flash-latest` from that live list. That's the difference between guessing and checking.

## One Flawed AI Suggestion

For most of the project, `app.py` hardcoded `pet = owner.pets[0]` in the Tasks section. Every new task silently went to whichever pet was added first, with no dropdown, no warning, nothing. For a single-pet demo this never showed up as a problem, but any owner with two or more pets would have had every task quietly assigned to the wrong animal. It wasn't flagged by a test or a bug report; it took explicitly asking "how can I add tasks for a specific pet?" for the gap to even surface.

## System's Limitations

- **No persistence.** Everything (owner, pets, tasks) lives in Streamlit `st.session_state` / process memory. Restarting the app loses all data. There's no database.
- **Single-user, no auth.** One `Owner` per running session; nothing about multi-user access or accounts.
- **Hard dependency on a live API for the AI feature.** Without `GEMINI_API_KEY` set, conflict resolution is fully disabled (fails gracefully, but there's no offline/local-model fallback).
- **Fixed retry ceiling.** `resolve_conflicts()` gives up after 2 attempts; a sufficiently tangled set of overlapping tasks can exhaust that and fall back to "manual review needed" with nothing resolved.
- **Hardcoded guardrail bounds.** The AI is only allowed to propose times between 06:00–22:00. Which is reasonable as a default, but not user-configurable.
- **No timezone or multi-day task support.** Times are plain `HH:MM` strings scoped to a single `due_date`; nothing models tasks spanning midnight or across timezones.
- **Model behavior can drift.** Using the `gemini-flash-latest` alias means Google can change what model actually answers a given prompt without any code change on this end.