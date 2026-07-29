import streamlit as st
from pawpal_system import Pet, Task, Owner
from ai_scheduler import resolve_conflicts

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

pet = owner.pets[0] if owner.pets else None

st.divider()

# ── Tasks ──────────────────────────────────────────────────────────────────
st.subheader("Tasks")

if pet is None:
    st.warning("Add a pet above before adding tasks.")
    st.stop()

st.caption(f"Adding tasks for **{pet.name}** {SPECIES_EMOJI.get(pet.species, '🐾')}")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
    task_time  = st.text_input("Time (HH:MM)", value="08:00")
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
    )
    owner.schedule.add_task(pet, task)
    st.rerun()

tasks = owner.schedule.get_tasks_for_pet(pet)

if tasks:
    st.markdown(f"**{len(tasks)} task(s) for {pet.name}:**")
    for i, t in enumerate(tasks):
        icon = PRIORITY_ICON.get(t.priority, "⚪")
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            if t.is_complete:
                st.markdown(f"{icon} ~~{t.task_type}~~ · {t.time} · {t.duration} min · _{t.frequency}_")
            else:
                st.markdown(f"{icon} **{t.task_type}** · {t.time} · {t.duration} min · _{t.frequency}_")
        with c2:
            if t.is_complete:
                st.success("done", icon="✅")
            else:
                st.caption("⏳ pending")
        with c3:
            if not t.is_complete and st.button("Mark done", key=f"done_{i}"):
                owner.schedule.mark_task_complete(pet, t)
                st.rerun()

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

if st.button("Generate schedule", type="primary"):
    sorted_tasks = owner.schedule.get_tasks_sorted_by_time()
    pending      = owner.schedule.get_all_pending_tasks()
    completed    = owner.schedule.get_all_completed_tasks()
    conflicts    = owner.schedule.get_conflicts()

    if not sorted_tasks:
        st.info("No tasks scheduled yet — add tasks above, then generate the schedule.")
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

        # Chronological table
        st.markdown("**Chronological schedule:**")
        st.dataframe(
            [
                {
                    "time":          t.time,
                    "task":          f"{PRIORITY_ICON.get(t.priority, '⚪')} {t.task_type}",
                    "duration (min)": t.duration,
                    "priority":      t.priority,
                    "status":        "✅ done" if t.is_complete else "⏳ pending",
                }
                for t in sorted_tasks
            ],
            use_container_width=True,
            hide_index=True,
        )
