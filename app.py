import streamlit as st
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
import anthropic

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Life Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Data persistence ──────────────────────────────────────────────────────────
DATA_FILE = Path("data/user_data.json")

def load_data() -> dict:
    DATA_FILE.parent.mkdir(exist_ok=True)
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "goals": [
            {"id": 1, "title": "Gym 4x per week", "category": "Fitness", "description": "Build strength and consistency", "progress": 50, "target": "4 sessions/week"},
            {"id": 2, "title": "Complete assignments on time", "category": "Study", "description": "Stay ahead of deadlines, study every day", "progress": 30, "target": "Daily study sessions"},
            {"id": 3, "title": "Daily mindfulness practice", "category": "Mental Health", "description": "10 min journaling or meditation each day", "progress": 65, "target": "10 min/day"},
        ],
        "tasks": [
            {"id": 1, "title": "Morning workout — legs day", "time": "07:30", "duration": 60, "category": "Fitness", "done": False, "ai_suggested": False, "date": str(date.today())},
            {"id": 2, "title": "Deep work block — assignment", "time": "10:00", "duration": 120, "category": "Study", "done": False, "ai_suggested": True, "date": str(date.today())},
            {"id": 3, "title": "10 min meditation", "time": "08:45", "duration": 10, "category": "Mental Health", "done": False, "ai_suggested": True, "date": str(date.today())},
        ],
        "deadlines": [
            {"id": 1, "title": "History essay due", "due_date": str(date.today() + timedelta(days=8)), "category": "Study", "notes": "2000 words, needs bibliography"},
            {"id": 2, "title": "Group project presentation", "due_date": str(date.today() + timedelta(days=16)), "category": "Study", "notes": "15 min slides"},
        ],
        "next_id": 10,
    }

def save_data(data: dict):
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── Session state ─────────────────────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data

# ── Helpers ───────────────────────────────────────────────────────────────────
CATEGORY_COLORS = {
    "Fitness":       "🟢",
    "Study":         "🔵",
    "Mental Health": "🟣",
    "Life":          "🟡",
}

CATEGORY_LIST = list(CATEGORY_COLORS.keys())

def days_until(due_str: str) -> int:
    return (date.fromisoformat(due_str) - date.today()).days

def fmt_duration(mins: int) -> str:
    if mins < 60:
        return f"{mins}m"
    h = mins // 60
    m = mins % 60
    return f"{h}h {m}m" if m else f"{h}h"

def next_id() -> int:
    nid = data["next_id"]
    data["next_id"] += 1
    return nid

def today_tasks():
    today = str(date.today())
    return [t for t in data["tasks"] if t.get("date") == today]

# ── AI plan generation ────────────────────────────────────────────────────────
def generate_ai_plan(api_key: str) -> list[dict]:
    client = anthropic.Anthropic(api_key=api_key)

    goals_txt = "\n".join(
        f"- {g['title']} ({g['category']}, {g['progress']}% progress, target: {g['target']})"
        for g in data["goals"]
    )
    deadlines_txt = "\n".join(
        f"- {d['title']} due in {days_until(d['due_date'])} days ({d['notes']})"
        for d in data["deadlines"]
        if days_until(d["due_date"]) >= 0
    ) or "None"

    prompt = f"""You are a personal productivity coach. Generate a smart daily plan for today.

GOALS:
{goals_txt}

UPCOMING DEADLINES:
{deadlines_txt}

Create exactly 5 tasks for today that are specific, actionable, and time-blocked.
Include at least one fitness task, one study/work task, and one mental health task.
For deadlines soon (under 7 days), include a focused work session.

Respond ONLY with a JSON array — no markdown, no extra text:
[
  {{
    "title": "Specific task name",
    "time": "HH:MM",
    "duration": 60,
    "category": "Fitness|Study|Mental Health|Life",
    "reason": "One sentence why this task matters today"
  }}
]
"""
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Life Dashboard")
    st.caption(datetime.now().strftime("%A, %d %B %Y"))
    st.divider()

    # Quick stats
    today_t = today_tasks()
    done_count = sum(1 for t in today_t if t["done"])
    total_count = len(today_t)
    total_hours = sum(t["duration"] for t in today_t) / 60

    col1, col2 = st.columns(2)
    col1.metric("Done today", f"{done_count}/{total_count}")
    col2.metric("Hours planned", f"{total_hours:.1f}h")

    st.divider()

    # API key
    st.subheader("⚡ AI Planner")
    api_key = st.text_input(
        "Anthropic API key",
        type="password",
        help="Get yours at console.anthropic.com",
        placeholder="sk-ant-...",
    )
    if not api_key:
        st.caption("Add your API key to enable AI planning")

    st.divider()

    # Upcoming deadlines
    st.subheader("📅 Deadlines")
    if data["deadlines"]:
        for d in sorted(data["deadlines"], key=lambda x: x["due_date"]):
            days = days_until(d["due_date"])
            color = "🔴" if days <= 3 else "🟠" if days <= 7 else "🟡"
            st.caption(f"{color} **{d['title']}** — {days}d")
    else:
        st.caption("No deadlines added yet")

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_today, tab_goals, tab_planner, tab_deadlines = st.tabs(
    ["📋 Today", "🎯 Goals", "🤖 AI Planner", "📅 Deadlines & Events"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TODAY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_today:
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.subheader("Today's tasks")

    with col_right:
        if st.button("＋ Add task", use_container_width=True):
            st.session_state.show_add_task = True

    tasks_today = sorted(today_tasks(), key=lambda t: t["time"])

    if not tasks_today:
        st.info("No tasks yet for today. Add one manually or use the AI Planner to generate your day!")
    else:
        for task in tasks_today:
            col_check, col_info, col_del = st.columns([0.5, 8, 0.5])

            with col_check:
                checked = st.checkbox(
                    "", value=task["done"],
                    key=f"check_{task['id']}",
                    label_visibility="collapsed"
                )
                if checked != task["done"]:
                    task["done"] = checked
                    # Nudge goal progress
                    for g in data["goals"]:
                        if g["category"] == task["category"] and checked:
                            g["progress"] = min(100, g["progress"] + 3)
                    save_data(data)
                    st.rerun()

            with col_info:
                icon = CATEGORY_COLORS.get(task["category"], "⚪")
                ai_badge = " `AI` " if task.get("ai_suggested") else ""
                style = "~~" if task["done"] else ""
                st.markdown(
                    f"{style}**{task['title']}**{style}  \n"
                    f"{icon} `{task['time']}` · `{fmt_duration(task['duration'])}` · {task['category']}{ai_badge}"
                )

            with col_del:
                if st.button("✕", key=f"del_{task['id']}", help="Remove task"):
                    data["tasks"] = [t for t in data["tasks"] if t["id"] != task["id"]]
                    save_data(data)
                    st.rerun()

            st.divider()

    # Add task form
    if st.session_state.get("show_add_task"):
        with st.form("add_task_form"):
            st.subheader("New task")
            t_title = st.text_input("Task title", placeholder="e.g. Read chapter 3")
            c1, c2, c3 = st.columns(3)
            t_time = c1.text_input("Time", value="09:00", placeholder="HH:MM")
            t_dur = c2.number_input("Duration (min)", min_value=5, max_value=480, value=60, step=5)
            t_cat = c3.selectbox("Category", CATEGORY_LIST)

            sub, cancel = st.columns(2)
            if sub.form_submit_button("Add task", use_container_width=True, type="primary"):
                if t_title:
                    data["tasks"].append({
                        "id": next_id(), "title": t_title, "time": t_time,
                        "duration": int(t_dur), "category": t_cat,
                        "done": False, "ai_suggested": False, "date": str(date.today())
                    })
                    save_data(data)
                    st.session_state.show_add_task = False
                    st.rerun()
            if cancel.form_submit_button("Cancel", use_container_width=True):
                st.session_state.show_add_task = False
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GOALS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_goals:
    col_l, col_r = st.columns([3, 1])
    col_l.subheader("My goals")
    if col_r.button("＋ Add goal", use_container_width=True):
        st.session_state.show_add_goal = True

    for goal in data["goals"]:
        with st.container(border=True):
            c1, c2 = st.columns([6, 1])
            with c1:
                icon = CATEGORY_COLORS.get(goal["category"], "⚪")
                st.markdown(f"#### {icon} {goal['title']}")
                st.caption(f"**{goal['category']}** · Target: {goal['target']}")
                st.write(goal["description"])
            with c2:
                new_prog = st.number_input(
                    "Progress %", 0, 100, goal["progress"],
                    key=f"prog_{goal['id']}", step=5
                )
                if new_prog != goal["progress"]:
                    goal["progress"] = new_prog
                    save_data(data)

            st.progress(goal["progress"] / 100)
            st.caption(f"{goal['progress']}% complete")

            if st.button("🗑 Remove", key=f"delgoal_{goal['id']}"):
                data["goals"] = [g for g in data["goals"] if g["id"] != goal["id"]]
                save_data(data)
                st.rerun()

    if st.session_state.get("show_add_goal"):
        with st.form("add_goal_form"):
            st.subheader("New goal")
            g_title = st.text_input("Goal title", placeholder="e.g. Run 5km three times a week")
            g_cat = st.selectbox("Category", CATEGORY_LIST)
            g_desc = st.text_area("Description", placeholder="What does success look like?")
            g_target = st.text_input("Target", placeholder="e.g. 3 sessions/week")

            sub2, can2 = st.columns(2)
            if sub2.form_submit_button("Save goal", use_container_width=True, type="primary"):
                if g_title:
                    data["goals"].append({
                        "id": next_id(), "title": g_title, "category": g_cat,
                        "description": g_desc or "No description",
                        "target": g_target or "Personal target",
                        "progress": 0,
                    })
                    save_data(data)
                    st.session_state.show_add_goal = False
                    st.rerun()
            if can2.form_submit_button("Cancel", use_container_width=True):
                st.session_state.show_add_goal = False
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI PLANNER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_planner:
    st.subheader("🤖 AI-powered daily planner")
    st.write(
        "Claude will look at your goals and upcoming deadlines to build a personalised task list for today. "
        "Review the suggestions and add the ones you want."
    )

    if not api_key:
        st.warning("Add your Anthropic API key in the sidebar to use this feature.")
    else:
        if st.button("✨ Generate today's plan", type="primary", use_container_width=False):
            with st.spinner("Thinking about your goals and deadlines..."):
                try:
                    suggestions = generate_ai_plan(api_key)
                    st.session_state.ai_suggestions = suggestions
                except Exception as e:
                    st.error(f"Could not generate plan: {e}")

        if "ai_suggestions" in st.session_state:
            st.divider()
            st.markdown("### Suggested tasks for today")
            st.caption("Click **Add** on the tasks you want in your day.")

            for i, task in enumerate(st.session_state.ai_suggestions):
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        icon = CATEGORY_COLORS.get(task.get("category"), "⚪")
                        st.markdown(f"**{icon} {task['title']}**")
                        st.caption(
                            f"`{task['time']}` · `{fmt_duration(task['duration'])}` · "
                            f"{task['category']}  \n💡 {task['reason']}"
                        )
                    with c2:
                        already = any(
                            t["title"] == task["title"] and t["date"] == str(date.today())
                            for t in data["tasks"]
                        )
                        if already:
                            st.success("Added ✓")
                        elif st.button("Add", key=f"ai_add_{i}", use_container_width=True):
                            data["tasks"].append({
                                "id": next_id(),
                                "title": task["title"],
                                "time": task["time"],
                                "duration": task["duration"],
                                "category": task["category"],
                                "done": False,
                                "ai_suggested": True,
                                "date": str(date.today()),
                            })
                            save_data(data)
                            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DEADLINES
# ═══════════════════════════════════════════════════════════════════════════════
with tab_deadlines:
    col_l2, col_r2 = st.columns([3, 1])
    col_l2.subheader("Upcoming deadlines & events")
    if col_r2.button("＋ Add deadline", use_container_width=True):
        st.session_state.show_add_deadline = True

    sorted_deadlines = sorted(data["deadlines"], key=lambda d: d["due_date"])

    if not sorted_deadlines:
        st.info("No deadlines yet. Add assignments, exams, or events here — the AI planner will factor them in.")
    else:
        for dl in sorted_deadlines:
            days = days_until(dl["due_date"])
            urgency = "🔴" if days <= 3 else "🟠" if days <= 7 else "🟡" if days <= 14 else "🟢"

            with st.container(border=True):
                c1, c2, c3 = st.columns([5, 2, 1])
                c1.markdown(f"**{urgency} {dl['title']}**  \n{dl.get('notes', '')}")
                c2.metric(
                    "Due",
                    f"{'Today!' if days == 0 else f'in {days} days'}",
                    dl["due_date"],
                    delta_color="off"
                )
                if c3.button("✕", key=f"deldl_{dl['id']}"):
                    data["deadlines"] = [d for d in data["deadlines"] if d["id"] != dl["id"]]
                    save_data(data)
                    st.rerun()

    if st.session_state.get("show_add_deadline"):
        with st.form("add_deadline_form"):
            st.subheader("New deadline / event")
            d_title = st.text_input("Title", placeholder="e.g. Biology assignment due")
            d_date = st.date_input("Due date", min_value=date.today())
            d_cat = st.selectbox("Category", CATEGORY_LIST)
            d_notes = st.text_input("Notes (optional)", placeholder="e.g. 1500 words, APA format")

            sub3, can3 = st.columns(2)
            if sub3.form_submit_button("Save", use_container_width=True, type="primary"):
                if d_title:
                    data["deadlines"].append({
                        "id": next_id(), "title": d_title,
                        "due_date": str(d_date), "category": d_cat,
                        "notes": d_notes or ""
                    })
                    save_data(data)
                    st.session_state.show_add_deadline = False
                    st.rerun()
            if can3.form_submit_button("Cancel", use_container_width=True):
                st.session_state.show_add_deadline = False
                st.rerun()
