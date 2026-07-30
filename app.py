from datetime import date, timedelta

import streamlit as st
from pawpal_system import Pet, Task, Owner
from ai_scheduler import resolve_conflicts


def date_label(due_date: date) -> str:
    today = date.today()
    if due_date == today:
        return "today"
    if due_date == today + timedelta(days=1):
        return "tomorrow"
    return due_date.strftime("%b %d")

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("A pet care planning assistant — build a schedule, spot conflicts, and track tasks.")

with st.expander("About this app", expanded=False):
    st.markdown(
        """
**PawPal+** helps a pet owner plan care tasks based on constraints like time, priority, and preferences.

Your system represents pets, tasks, and an owner, then builds and explains a daily schedule.
"""
    )

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
SPECIES_EMOJI = {"dog": "🐶", "cat": "🐱", "other": "🐾"}

DONE_PILL_HTML = (
    '<div style="background-color:rgba(33,195,84,0.15);color:rgb(23,114,51);'
    'border-radius:0.5rem;padding:0.5rem 0.75rem;text-align:center;font-size:0.875rem;">'
    "✅ done</div>"
)


def done_pill():
    st.markdown(DONE_PILL_HTML, unsafe_allow_html=True)

st.divider()

# ── Owner ──────────────────────────────────────────────────────────────────
st.subheader("Owner")
col1, col2, col3 = st.columns(3)
owner_name    = col1.text_input("Name",    value="Jordan")
owner_address = col2.text_input("Address", value="123 Main St")
owner_phone   = col3.text_input("Phone",   value="555-1234")

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name, address=owner_address, phone=owner_phone)

owner: Owner = st.session_state.owner
owner.name = owner_name

st.divider()

# ── Pets ───────────────────────────────────────────────────────────────────
st.subheader("Your Pets")

if owner.pets:
    st.table([
        {
            "": SPECIES_EMOJI.get(p.species, "🐾"),
            "name": p.name,
            "species": p.species,
            "age (yrs)": p.age,
            "medications": ", ".join(p.medications) if p.medications else "none",
        }
        for p in owner.pets
    ])
else:
    st.info("No pets yet — add one below.")

with st.form("add_pet_form"):
    st.markdown("**Add a pet**")
    c1, c2 = st.columns(2)
    with c1:
        new_pet_name  = st.text_input("Pet name", value="Mochi")
        new_age       = st.number_input("Age", min_value=0, max_value=30, value=5)
    with c2:
        new_species     = st.selectbox("Species", ["dog", "cat", "other"])
        new_medications = st.text_input("Medications (comma-separated)", value="")
    if st.form_submit_button("Add pet"):
        new_pet = Pet(
            name=new_pet_name,
            species=new_species,
            age=int(new_age),
            medications=[m.strip() for m in new_medications.split(",") if m.strip()],
        )
        st.session_state.owner.add_pet(new_pet)
        st.rerun()

st.divider()

# ── Tasks ──────────────────────────────────────────────────────────────────
st.subheader("Tasks")

if not owner.pets:
    st.warning("Add a pet above before adding tasks.")
    st.stop()

pet_index = st.selectbox(
    "Pet",
    options=range(len(owner.pets)),
    format_func=lambda i: f"{owner.pets[i].name} {SPECIES_EMOJI.get(owner.pets[i].species, '🐾')}",
)
pet = owner.pets[pet_index]

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
    task_time  = st.text_input("Time (HH:MM)", value="08:00")
    task_due_date = st.date_input("Due date", value=date.today())
with col2:
    duration  = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
with col3:
    priority    = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    description = st.text_input("Description", value="")

if st.button("Add task", type="primary"):
    task = Task.create_task(
        task_type=task_title,
        duration=int(duration),
        priority=priority,
        description=description,
        time=task_time,
        frequency=frequency,
        pet=pet,
        due_date=task_due_date,
    )
    owner.schedule.add_task(pet, task)
    st.rerun()

tasks = owner.schedule.get_tasks_for_pet(pet)

if tasks:
    st.markdown(f"**{len(tasks)} task(s) for {pet.name}:**")
    for t in tasks:
        icon = PRIORITY_ICON.get(t.priority, "⚪")
        c1, c2 = st.columns([5, 1])
        with c1:
            label = date_label(t.due_date)
            if t.is_complete:
                st.markdown(f"{icon} ~~{t.task_type}~~ · _{label}_ {t.time} · {t.duration} min · _{t.frequency}_")
            else:
                st.markdown(f"{icon} **{t.task_type}** · _{label}_ {t.time} · {t.duration} min · _{t.frequency}_")
        with c2:
            if t.is_complete:
                st.caption("✅ done")
            else:
                st.caption("⏳ pending")
    st.caption("Mark tasks done from today's plan in the Build Schedule section below.")

    RESOLUTION_ICON = {"success": "✅", "warning": "⚠️", "error": "🚫"}
    if "ai_resolution_message" in st.session_state:
        level, message = st.session_state.pop("ai_resolution_message")
        getattr(st, level)(message, icon=RESOLUTION_ICON[level])

    conflicts = owner.schedule.get_conflicts()
    if conflicts:
        for w in conflicts:
            st.error(w, icon="⚠️")
        if st.button("🤖 Resolve conflicts with AI"):
            try:
                with st.spinner("Asking Gemini to propose new times..."):
                    result = resolve_conflicts(owner.schedule)
            except RuntimeError as exc:
                st.session_state.ai_resolution_message = ("error", str(exc))
            else:
                level = "success" if result.applied else "warning"
                st.session_state.ai_resolution_message = (level, result.explanation)
            st.rerun()
    else:
        st.success("No scheduling conflicts.", icon="✅")
else:
    st.info("No tasks yet — add one above.")

st.divider()

# ── Schedule ───────────────────────────────────────────────────────────────
st.subheader("Build Schedule")
st.caption(f"Today's plan — {date.today().strftime('%B %d, %Y')}. Recurring tasks due on other days won't clutter this view.")

if st.button("Generate schedule", type="primary"):
    st.session_state.schedule_generated = True

if st.session_state.get("schedule_generated"):
    sorted_tasks = owner.schedule.get_tasks_sorted_by_time(due_date=date.today())
    pending      = [t for t in sorted_tasks if not t.is_complete]
    completed    = [t for t in sorted_tasks if t.is_complete]
    conflicts    = owner.schedule.get_conflicts(due_date=date.today())

    if not sorted_tasks:
        st.info("No tasks due today — add tasks above, then generate the schedule.")
    else:
        # Conflict status banner
        if conflicts:
            for w in conflicts:
                st.error(w, icon="⚠️")
        else:
            st.success("Schedule is conflict-free!", icon="✅")

        # Summary metrics
        total = len(sorted_tasks)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total tasks",  total)
        c2.metric("Pending",      len(pending))
        c3.metric("Completed",    len(completed))

        if total > 0:
            pct = len(completed) / total
            st.progress(pct, text=f"{len(completed)} of {total} tasks complete")

        # Chronological schedule with inline completion
        st.markdown("**Chronological schedule:**")
        for i, t in enumerate(sorted_tasks):
            icon = PRIORITY_ICON.get(t.priority, "⚪")
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                if t.is_complete:
                    st.markdown(f"{icon} ~~{t.task_type}~~ · {t.time} · {t.duration} min · _{t.pet.name}_")
                else:
                    st.markdown(f"{icon} **{t.task_type}** · {t.time} · {t.duration} min · _{t.pet.name}_")
            with c2:
                if t.is_complete:
                    done_pill()
                else:
                    st.caption("⏳ pending")
            with c3:
                if not t.is_complete and st.button("Mark done", key=f"sched_done_{i}"):
                    owner.schedule.mark_task_complete(t.pet, t)
                    st.rerun()
