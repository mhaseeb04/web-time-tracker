import streamlit as st
import sqlite3
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import json

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="🎯 Smart Productivity Tracker", 
    layout="wide", 
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .warning-message {
        background: #fff3cd;
        color: #856404;
        padding: 0.75rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
@st.cache_resource
def init_database():
    conn = sqlite3.connect("enhanced_time_tracker.db", check_same_thread=False)
    c = conn.cursor()
    
    # Activities table
    c.execute('''
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        subcategory TEXT,
        description TEXT,
        duration INTEGER,
        date TEXT,
        tags TEXT,
        productivity_rating INTEGER,
        mood TEXT,
        location TEXT
    )
    ''')
    
    # Goals table
    c.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        category TEXT PRIMARY KEY,
        daily_goal INTEGER,
        weekly_goal INTEGER,
        monthly_goal INTEGER,
        priority INTEGER
    )
    ''')
    
    # Settings table
    c.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    # Achievements table
    c.execute('''
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        earned_date TEXT,
        category TEXT
    )
    ''')
    
    conn.commit()
    return conn

conn = init_database()
c = conn.cursor()

# --- CONFIGURATION ---
CATEGORIES = {
    "Study": {"icon": "📚", "color": "#3498db", "subcategories": ["Mathematics", "Science", "Languages", "Research", "Reading"]},
    "Work": {"icon": "💼", "color": "#e74c3c", "subcategories": ["Meetings", "Development", "Documentation", "Planning", "Email"]},
    "Exercise": {"icon": "🏃‍♂️", "color": "#27ae60", "subcategories": ["Cardio", "Strength", "Yoga", "Sports", "Walking"]},
    "Project": {"icon": "🛠️", "color": "#f39c12", "subcategories": ["Personal", "Side Business", "Learning", "Creative", "Hobby"]},
    "Class": {"icon": "🎓", "color": "#9b59b6", "subcategories": ["Lecture", "Lab", "Tutorial", "Discussion", "Presentation"]},
    "Personal": {"icon": "🌟", "color": "#1abc9c", "subcategories": ["Health", "Family", "Friends", "Hobbies", "Self-care"]}
}

MOODS = ["😊 Great", "🙂 Good", "😐 Okay", "😔 Poor", "😴 Tired"]
LOCATIONS = ["🏠 Home", "🏢 Office", "📚 Library", "☕ Cafe", "🚗 Commute", "🏖️ Other"]

# --- UTILITY FUNCTIONS ---
def format_duration(minutes):
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"

def get_streak_days(category):
    """Calculate consecutive days with activity in a category"""
    query = """
    SELECT DISTINCT date(date) as day 
    FROM activities 
    WHERE category = ? AND date >= date('now', '-30 days')
    ORDER BY day DESC
    """
    days = c.execute(query, (category,)).fetchall()
    
    if not days:
        return 0
    
    streak = 0
    current_date = date.today()
    
    for day_tuple in days:
        day = datetime.strptime(day_tuple[0], '%Y-%m-%d').date()
        if day == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        elif day == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    return streak

def check_achievements():
    """Check and award new achievements"""
    achievements = []
    total_hours = c.execute("SELECT SUM(duration) FROM activities").fetchone()[0] or 0
    total_hours = total_hours // 60
    
    # Hour-based achievements
    hour_milestones = [(10, "First Steps", "Logged your first 10 hours"), 
                       (50, "Getting Serious", "Reached 50 hours"),
                       (100, "Century Club", "Amazing! 100 hours logged")]
    
    for milestone, title, desc in hour_milestones:
        if total_hours >= milestone:
            existing = c.execute("SELECT id FROM achievements WHERE title=?", (title,)).fetchone()
            if not existing:
                c.execute("INSERT INTO achievements (title, description, earned_date, category) VALUES (?, ?, ?, ?)",
                         (title, desc, datetime.now().strftime("%Y-%m-%d"), "Hours"))
                achievements.append(f"🏆 Achievement unlocked: {title}!")
    
    conn.commit()
    return achievements

# --- HEADER ---
st.markdown("""
<div class="main-header">
    <h1>🎯 Smart Productivity Tracker</h1>
    <p>Transform your time into achievements with intelligent tracking and insights</p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Quick Actions")
    
    # Quick Timer
    st.subheader("⏱️ Quick Timer")
    quick_category = st.selectbox("Category", list(CATEGORIES.keys()), key="quick_cat")
    quick_minutes = st.selectbox("Duration", [5, 10, 15, 25, 30, 45, 60], key="quick_min")
    
    if st.button("🚀 Start Quick Session", type="primary"):
        st.session_state.quick_timer = {
            'start': datetime.now(),
            'category': quick_category,
            'duration': quick_minutes,
            'active': True
        }
    
    # Show active quick timer
    if hasattr(st.session_state, 'quick_timer') and st.session_state.quick_timer.get('active'):
        elapsed = datetime.now() - st.session_state.quick_timer['start']
        elapsed_minutes = int(elapsed.total_seconds() / 60)
        remaining = st.session_state.quick_timer['duration'] - elapsed_minutes
        
        if remaining > 0:
            st.info(f"⏱️ {remaining} min remaining\n\n{st.session_state.quick_timer['category']}")
            if st.button("⏹️ Complete Session"):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO activities (category, description, duration, date, mood, productivity_rating) VALUES (?, ?, ?, ?, ?, ?)",
                         (st.session_state.quick_timer['category'], "Quick session", elapsed_minutes, timestamp, "🙂 Good", 4))
                conn.commit()
                st.success(f"Session completed! {elapsed_minutes} minutes logged.")
                st.session_state.quick_timer['active'] = False
                st.rerun()
        else:
            st.success("🎉 Quick session completed!")
            st.session_state.quick_timer['active'] = False
    
    st.divider()
    
    # Today's summary
    st.subheader("📊 Today's Summary")
    today_str = date.today().strftime("%Y-%m-%d")
    today_total = c.execute("SELECT SUM(duration) FROM activities WHERE date LIKE ?", (today_str + "%",)).fetchone()[0] or 0
    st.metric("Total Time", format_duration(today_total))
    
    # Achievements notification
    new_achievements = check_achievements()
    for achievement in new_achievements:
        st.success(achievement)

# --- MAIN TABS ---
tabs = st.tabs(["📊 Dashboard", "⏱️ Advanced Timer", "➕ Add Activity", "📈 Analytics", "🎯 Goals & Progress", "📋 Activity Log", "🏆 Achievements"])

# --- DASHBOARD TAB ---
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    
    # Key metrics
    total_time = c.execute("SELECT SUM(duration) FROM activities").fetchone()[0] or 0
    today_time = c.execute("SELECT SUM(duration) FROM activities WHERE date LIKE ?", (today_str + "%",)).fetchone()[0] or 0
    this_week = c.execute("SELECT SUM(duration) FROM activities WHERE date >= ?", ((date.today() - timedelta(days=7)).strftime("%Y-%m-%d") + "%",)).fetchone()[0] or 0
    avg_daily = c.execute("SELECT AVG(daily_total) FROM (SELECT SUM(duration) as daily_total FROM activities GROUP BY date(date))").fetchone()[0] or 0
    
    with col1:
        st.metric("🎯 Total Hours", f"{total_time//60}h", f"{total_time%60}m")
    with col2:
        st.metric("📅 Today", format_duration(today_time))
    with col3:
        st.metric("📊 This Week", format_duration(this_week))
    with col4:
        st.metric("📈 Daily Average", format_duration(int(avg_daily)))
    
    st.divider()
    
    # Today's breakdown
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Today's Activity Breakdown")
        today_data = c.execute("""
        SELECT category, SUM(duration) as total, AVG(productivity_rating) as avg_rating
        FROM activities 
        WHERE date LIKE ? 
        GROUP BY category
        """, (today_str + "%",)).fetchall()
        
        if today_data:
            df_today = pd.DataFrame(today_data, columns=["Category", "Duration", "Avg Rating"])
            
            # Create pie chart
            fig = px.pie(df_today, values='Duration', names='Category', 
                        color_discrete_map={cat: CATEGORIES[cat]["color"] for cat in CATEGORIES.keys()})
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No activities logged today. Start tracking to see your breakdown!")
    
    with col2:
        st.subheader("🔥 Current Streaks")
        for category in CATEGORIES.keys():
            streak = get_streak_days(category)
            if streak > 0:
                st.metric(f"{CATEGORIES[category]['icon']} {category}", f"{streak} days", delta=f"🔥")
        
        # Motivation message
        st.markdown("---")
        st.markdown("### 💪 Today's Motivation")
        motivations = [
            "Every minute counts toward your goals!",
            "Consistency beats perfection.",
            "You're building great habits!",
            "Small steps lead to big changes.",
            "Track it, improve it, master it!"
        ]
        import random
        st.info(random.choice(motivations))

# --- ADVANCED TIMER TAB ---
with tabs[1]:
    st.header("⏱️ Advanced Timer")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎯 Session Setup")
        
        timer_category = st.selectbox("Category", list(CATEGORIES.keys()), key="timer_cat")
        timer_subcategory = st.selectbox("Subcategory", CATEGORIES[timer_category]["subcategories"], key="timer_subcat")
        timer_description = st.text_area("What are you working on?", key="timer_desc")
        timer_tags = st.text_input("Tags (comma-separated)", placeholder="e.g., important, deadline, review", key="timer_tags")
        
        col_mood, col_location = st.columns(2)
        with col_mood:
            timer_mood = st.selectbox("Current Mood", MOODS, key="timer_mood")
        with col_location:
            timer_location = st.selectbox("Location", LOCATIONS, key="timer_location")
        
        # Pomodoro settings
        st.subheader("🍅 Pomodoro Settings")
        use_pomodoro = st.checkbox("Use Pomodoro Technique")
        if use_pomodoro:
            work_minutes = st.slider("Work Duration (minutes)", 15, 60, 25)
            break_minutes = st.slider("Break Duration (minutes)", 5, 30, 5)
            long_break = st.slider("Long Break Duration (minutes)", 15, 60, 30)
            sessions_before_long_break = st.slider("Sessions before long break", 2, 8, 4)
    
    with col2:
        st.subheader("⏱️ Timer Controls")
        
        # Initialize timer state
        if "advanced_timer" not in st.session_state:
            st.session_state.advanced_timer = {
                'active': False,
                'start_time': None,
                'elapsed': 0,
                'is_break': False,
                'pomodoro_count': 0
            }
        
        timer_state = st.session_state.advanced_timer
        
        # Timer display
        if timer_state['active']:
            current_elapsed = datetime.now() - timer_state['start_time']
            total_elapsed = timer_state['elapsed'] + int(current_elapsed.total_seconds() / 60)
            
            # Pomodoro logic
            if use_pomodoro:
                target_duration = break_minutes if timer_state['is_break'] else work_minutes
                remaining = max(0, target_duration - (total_elapsed % target_duration))
                
                if remaining == 0 and not timer_state['is_break']:
                    # Work session completed
                    st.success("🎉 Work session completed!")
                    timer_state['pomodoro_count'] += 1
                    if timer_state['pomodoro_count'] % sessions_before_long_break == 0:
                        st.info(f"Time for a {long_break}-minute long break!")
                    else:
                        st.info(f"Time for a {break_minutes}-minute break!")
                
                phase = "Break" if timer_state['is_break'] else "Work"
                st.metric(f"⏱️ {phase} Time", f"{remaining} min remaining")
            else:
                st.metric("⏱️ Elapsed Time", format_duration(total_elapsed))
        
        # Control buttons
        col_start, col_pause, col_stop = st.columns(3)
        
        with col_start:
            if st.button("▶️ Start", disabled=timer_state['active']):
                timer_state['active'] = True
                timer_state['start_time'] = datetime.now()
        
        with col_pause:
            if st.button("⏸️ Pause", disabled=not timer_state['active']):
                if timer_state['active']:
                    elapsed_now = datetime.now() - timer_state['start_time']
                    timer_state['elapsed'] += int(elapsed_now.total_seconds() / 60)
                    timer_state['active'] = False
        
        with col_stop:
            if st.button("⏹️ Stop & Save"):
                if timer_state['active']:
                    elapsed_now = datetime.now() - timer_state['start_time']
                    total_duration = timer_state['elapsed'] + int(elapsed_now.total_seconds() / 60)
                else:
                    total_duration = timer_state['elapsed']
                
                if total_duration > 0:
                    # Save to database
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    productivity_rating = st.slider("How productive was this session?", 1, 5, 3, key="prod_rating")
                    
                    c.execute("""
                    INSERT INTO activities 
                    (category, subcategory, description, duration, date, tags, productivity_rating, mood, location) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (timer_category, timer_subcategory, timer_description, total_duration, 
                          timestamp, timer_tags, productivity_rating, timer_mood, timer_location))
                    conn.commit()
                    
                    st.success(f"🎉 Session saved! {format_duration(total_duration)} logged for {timer_category}")
                
                # Reset timer
                timer_state['active'] = False
                timer_state['start_time'] = None
                timer_state['elapsed'] = 0
                timer_state['pomodoro_count'] = 0

# --- ADD ACTIVITY TAB ---
with tabs[2]:
    st.header("➕ Add Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        add_category = st.selectbox("Category", list(CATEGORIES.keys()))
        add_subcategory = st.selectbox("Subcategory", CATEGORIES[add_category]["subcategories"])
        add_description = st.text_area("Description")
        add_duration = st.number_input("Duration (minutes)", min_value=1, value=30)
        add_date = st.date_input("Date", value=date.today())
        add_time = st.time_input("Time", value=datetime.now().time())
    
    with col2:
        add_tags = st.text_input("Tags (comma-separated)")
        add_mood = st.selectbox("Mood during activity", MOODS)
        add_location = st.selectbox("Location", LOCATIONS)
        add_rating = st.slider("Productivity Rating", 1, 5, 3, help="1=Very Low, 5=Very High")
        
        # Add custom category option
        st.markdown("---")
        if st.checkbox("Add custom category"):
            custom_category = st.text_input("Custom Category Name")
            custom_icon = st.text_input("Icon (emoji)", value="⭐")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Activity", type="primary"):
            category_to_use = add_category
            if 'custom_category' in locals() and custom_category:
                category_to_use = custom_category
                # Add to categories for this session
                CATEGORIES[custom_category] = {"icon": custom_icon, "color": "#95a5a6"}
            
            timestamp = datetime.combine(add_date, add_time).strftime("%Y-%m-%d %H:%M:%S")
            c.execute("""
            INSERT INTO activities 
            (category, subcategory, description, duration, date, tags, productivity_rating, mood, location) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (category_to_use, add_subcategory, add_description, add_duration, 
                  timestamp, add_tags, add_rating, add_mood, add_location))
            conn.commit()
            st.success("✅ Activity saved successfully!")
    
    with col2:
        if st.button("📊 Save & View Stats"):
            # Save and show immediate impact
            pass
    
    with col3:
        if st.button("🔄 Save & Add Another"):
            # Save and clear form
            pass

# --- ANALYTICS TAB ---
with tabs[3]:
    st.header("📈 Advanced Analytics")
    
    # Date range selector
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("From", value=date.today()-timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=date.today())
    with col3:
        analysis_category = st.selectbox("Focus Category", ["All"] + list(CATEGORIES.keys()))
    
    # Fetch data
    date_filter = f"date >= '{start_date}' AND date <= '{end_date} 23:59:59'"
    category_filter = f"AND category = '{analysis_category}'" if analysis_category != "All" else ""
    
    analytics_data = c.execute(f"""
    SELECT category, subcategory, duration, date, productivity_rating, mood, location
    FROM activities 
    WHERE {date_filter} {category_filter}
    ORDER BY date
    """).fetchall()
    
    if analytics_data:
        df_analytics = pd.DataFrame(analytics_data, 
                                   columns=["Category", "Subcategory", "Duration", "Date", "Rating", "Mood", "Location"])
        df_analytics['Date'] = pd.to_datetime(df_analytics['Date']).dt.date
        
        # Time trends
        st.subheader("📊 Time Trends")
        daily_totals = df_analytics.groupby(['Date', 'Category'])['Duration'].sum().unstack(fill_value=0)
        
        fig = px.line(daily_totals.reset_index(), x='Date', y=daily_totals.columns.tolist(), 
                     title="Daily Activity Trends")
        st.plotly_chart(fig, use_container_width=True)
        
        # Productivity insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Productivity Insights")
            avg_rating = df_analytics['Rating'].mean()
            st.metric("Average Productivity", f"{avg_rating:.1f}/5")
            
            # Best performing categories
            category_performance = df_analytics.groupby('Category').agg({
                'Rating': 'mean',
                'Duration': 'sum'
            }).round(2)
            st.dataframe(category_performance)
        
        with col2:
            st.subheader("🌟 Mood Analysis")
            mood_dist = df_analytics['Mood'].value_counts()
            fig_mood = px.pie(values=mood_dist.values, names=mood_dist.index, 
                            title="Mood Distribution")
            st.plotly_chart(fig_mood, use_container_width=True)
        
        # Heatmap
        st.subheader("🔥 Activity Heatmap")
        df_analytics['Hour'] = pd.to_datetime(df_analytics['Date']).dt.hour
        df_analytics['Weekday'] = pd.to_datetime(df_analytics['Date']).dt.day_name()
        
        heatmap_data = df_analytics.groupby(['Weekday', 'Hour'])['Duration'].sum().unstack(fill_value=0)
        
        fig_heatmap = px.imshow(heatmap_data, 
                              labels=dict(x="Hour of Day", y="Day of Week", color="Minutes"),
                              title="Activity Intensity Heatmap")
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
    else:
        st.info("No data available for the selected period. Start tracking to see analytics!")

# --- GOALS & PROGRESS TAB ---
with tabs[4]:
    st.header("🎯 Goals & Progress Management")
    
    tab_set_goals, tab_view_progress = st.tabs(["Set Goals", "View Progress"])
    
    with tab_set_goals:
        st.subheader("🎯 Set Your Goals")
        
        for category in CATEGORIES.keys():
            st.markdown(f"### {CATEGORIES[category]['icon']} {category}")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                daily = st.number_input(f"Daily (min)", min_value=0, key=f"daily_{category}")
            with col2:
                weekly = st.number_input(f"Weekly (min)", min_value=0, key=f"weekly_{category}")
            with col3:
                monthly = st.number_input(f"Monthly (min)", min_value=0, key=f"monthly_{category}")
            with col4:
                priority = st.selectbox("Priority", ["Low", "Medium", "High"], key=f"priority_{category}")
            
            if st.button(f"💾 Save {category} Goals"):
                priority_num = {"Low": 1, "Medium": 2, "High": 3}[priority]
                c.execute("""
                INSERT OR REPLACE INTO goals 
                (category, daily_goal, weekly_goal, monthly_goal, priority) 
                VALUES (?, ?, ?, ?, ?)
                """, (category, daily, weekly, monthly, priority_num))
                conn.commit()
                st.success(f"Goals updated for {category}!")
    
    with tab_view_progress:
        st.subheader("📊 Progress Overview")
        
        goals_data = c.execute("SELECT * FROM goals ORDER BY priority DESC").fetchall()
        
        for goal in goals_data:
            category, daily_goal, weekly_goal, monthly_goal, priority = goal
            
            if category in CATEGORIES:
                st.markdown(f"### {CATEGORIES[category]['icon']} {category}")
                
                # Calculate current progress
                today_total = c.execute("SELECT SUM(duration) FROM activities WHERE category=? AND date LIKE ?",
                                      (category, today_str + "%")).fetchone()[0] or 0
                
                week_start = date.today() - timedelta(days=date.today().weekday())
                week_total = c.execute("SELECT SUM(duration) FROM activities WHERE category=? AND date >= ?",
                                     (category, week_start.strftime("%Y-%m-%d"))).fetchone()[0] or 0
                
                month_start = date.today().replace(day=1)
                month_total = c.execute("SELECT SUM(duration) FROM activities WHERE category=? AND date >= ?",
                                      (category, month_start.strftime("%Y-%m-%d"))).fetchone()[0] or 0
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    daily_progress = min(today_total / daily_goal, 1.0) if daily_goal > 0 else 0
                    st.metric("Daily Progress", f"{today_total}/{daily_goal} min")
                    st.progress(daily_progress)
                    if daily_progress >= 1.0:
                        st.success("🎉 Daily goal achieved!")
                
                with col2:
                    weekly_progress = min(week_total / weekly_goal, 1.0) if weekly_goal > 0 else 0
                    st.metric("Weekly Progress", f"{week_total}/{weekly_goal} min")
                    st.progress(weekly_progress)
                    if weekly_progress >= 1.0:
                        st.success("🏆 Weekly goal achieved!")
                
                with col3:
                    monthly_progress = min(month_total / monthly_goal, 1.0) if monthly_goal > 0 else 0
                    st.metric("Monthly Progress", f"{month_total}/{monthly_goal} min")
                    st.progress(monthly_progress)
                    if monthly_progress >= 1.0:
                        st.success("👑 Monthly goal achieved!")
                
                st.divider()

# --- ACTIVITY LOG TAB ---
with tabs[5]:
    st.header("📋 Activity Log & Management")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_category = st.selectbox("Filter by Category", ["All"] + list(CATEGORIES.keys()))
    with col2:
        filter_days = st.selectbox("Show last", ["7 days", "30 days", "90 days", "All time"])
    with col3:
        min_rating = st.slider("Min Productivity Rating", 1, 5, 1)
    with col4:
        search_term = st.text_input("Search in descriptions")
    
    # Build query
    conditions = []
    params = []
    
    if filter_category != "All":
        conditions.append("category = ?")
        params.append(filter_category)
    
    if filter_days != "All time":
        days_map = {"7 days": 7, "30 days": 30, "90 days": 90}
        days_ago = date.today() - timedelta(days=days_map[filter_days])
        conditions.append("date >= ?")
        params.append(days_ago.strftime("%Y-%m-%d"))
    
    conditions.append("productivity_rating >= ?")
    params.append(min_rating)
    
    if search_term:
        conditions.append("description LIKE ?")
        params.append(f"%{search_term}%")
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Fetch filtered data
    entries = c.execute(f"""
    SELECT id, category, subcategory, description, duration, date, tags, productivity_rating, mood, location
    FROM activities 
    {where_clause}
    ORDER BY date DESC
    """, params).fetchall