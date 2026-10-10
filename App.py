import matplotlib.pyplot as plt
import pandas as pd
import customtkinter as ctk  # Build entire Graphical User Interface
import sqlite3
import threading  # for multitasking support
import time  # for time tracking
import psutil  # for system monitoring
import win32gui  # for window management
import win32process  # for process management

from datetime import datetime  # for date and time management
from tkinter import messagebox  # for displaying message boxes

# Database
conn = sqlite3.connect('screen_time.db')
cursor = conn.cursor()  # Create a table to store screen time database
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usage  (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT,
        usage_seconds INTEGER,
        date TEXT
    )
''')

conn.commit()  # Commit save changes to the database


# Tracker
tracking = False  # Flag to track if tracking is active
usage_data = {}  # Dictionary to store usage data
session_seconds = 0  # Variable to track session time in seconds
session_id = 0  # Identifies the current tracking session (stops old threads)
timer_job = None  # Handle of the scheduled timer update
data_lock = threading.Lock()  # Protects usage_data between threads


def get_active_app():
    try:
        # Get the active Windows window
        hwnd = win32gui.GetForegroundWindow()

        # Get the active window title
        window_title = win32gui.GetWindowText(hwnd).lower()

        # Get the process ID
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        # Get the process information
        process = psutil.Process(pid)
        process_name = process.name().lower()

        # Identify websites from the active browser tab title
        if "youtube" in window_title:
            return "YouTube"

        elif "facebook" in window_title:
            return "Facebook"

        elif "instagram" in window_title:
            return "Instagram"

        # Identify browsers when another website is active
        browser_names = {
            "chrome.exe": "Google Chrome",
            "brave.exe": "Brave Browser",
            "msedge.exe": "Microsoft Edge",
            "firefox.exe": "Mozilla Firefox",
            "opera.exe": "Opera Browser"
        }

        if process_name in browser_names:
            return browser_names[process_name]

        # Return the actual application name for other programs
        return process.name()

    except Exception:
        return "Unknown"



def tracking_loop(my_session):
    # Runs in a background thread without updating the UI
    while tracking and my_session == session_id:

        active_app = get_active_app()

        with data_lock:
            usage_data[active_app] = (
                usage_data.get(active_app, 0) + 1
            )

        time.sleep(1)



# Database Storage
def save_to_database():
    today = datetime.now().strftime("%Y-%m-%d")  # Get the current date
    with data_lock:
        rows = list(usage_data.items())
    for app_name, usage_seconds in rows:
        cursor.execute('''
            INSERT INTO usage (
                app_name,
                usage_seconds,
                date)
            VALUES (?, ?, ?)
        ''', (app_name, usage_seconds, today))  # Insert usage data into the database
    conn.commit()  # Commit once after all rows are inserted


def update_dashboard():
    with data_lock:
        data = dict(usage_data)  # Safe copy

    total_seconds = sum(data.values())  # Calculate total usage time
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    total_time_label.configure(
        text=f"Total Time: {hours:02}:{minutes:02}:{seconds:02}"
        )  # Update the total time label

    sorted_apps = sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
        )  # Sort the applications by usage time in descending order

    text = ""

    for app_name, sec in sorted_apps[:5]:  # Limit to top 5 applications
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        text += f"{app_name:<25}{h:02}:{m:02}:{s:02}\n"

    app_usage_frame.configure(
        text=text if text else "No data available"
        )  # Update the application usage frame


def update_live_timer():
    global session_seconds, timer_job

    if tracking:
        session_seconds += 1

        hours = session_seconds // 3600
        minutes = (session_seconds % 3600) // 60
        seconds = session_seconds % 60

        timer_label.configure(
            text=f"{hours:02}:{minutes:02}:{seconds:02}"
            )  # 02 means always show 2 digits, even if the number is less than 10

        update_dashboard()  # UI update happens here, on the main thread
        timer_job = app.after(1000, update_live_timer)  # Schedule the next update


def start_tracking():
    global tracking, session_seconds, session_id, timer_job

    if tracking:
        return  # If tracking is already active, do nothing

    tracking = True  # Set tracking flag to True
    session_seconds = 0  # Reset session time
    session_id += 1  # New session, old threads will exit
    with data_lock:
        usage_data.clear()  # Reset usage data
    status_label.configure(text="Tracking...")  # Update status label

    timer_job = app.after(1000, update_live_timer)
    threading.Thread(
        target=tracking_loop,
        args=(session_id,),
        daemon=True
        ).start()  # Start the tracking loop in a separate thread


def stop_tracking():
    global tracking, timer_job

    if not tracking:
        return  # Nothing to stop (also prevents saving the same data twice)

    tracking = False
    if timer_job is not None:
        app.after_cancel(timer_job)  # Stop the live timer
        timer_job = None

    timer_label.configure(text="00:00:00")  # Reset the timer label
    update_dashboard()  # Show final numbers
    save_to_database()  # Save the usage data to the database
    status_label.configure(text="Tracking stopped.")  # Update status label


def show_chart():
    with data_lock:
        data = dict(usage_data)

    if not data:
        messagebox.showwarning(
            "No Data",
            "Track some apps before viewing the chart."
            )
        return

    apps = list(data.keys())
    seconds = list(data.values())

    plt.figure(figsize=(10, 6))
    plt.pie(
        seconds,
        labels=apps,
        autopct='%1.1f%%'
        )

    plt.title("App Usage Distribution")
    plt.show()  # Display the pie chart


def export_data():
    with data_lock:
        data = dict(usage_data)

    if not data:
        messagebox.showwarning(
            "No Data",
            "Track some apps before exporting data."
            )
        return

    df = pd.DataFrame(
        {
            "Application": list(data.keys()),
            "Seconds used": list(data.values())
        }
        )  # Create a DataFrame from the usage data

    filename = f"screen_time_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    df.to_csv(
        filename,
        index=False
        )

    messagebox.showinfo(
        "Export Successful",
        f"Data exported to {filename}"
        )


# UI
ctk.set_appearance_mode("system")  # Set the appearance mode to system default
ctk.set_default_color_theme("blue")  # Set the default color theme to blue

app = ctk.CTk()  # Create the main application window
app.geometry("800x600")
app.minsize(700, 500)  # Keeps the layout from collapsing when resized
app.title("Screen Time Tracker")
app.configure(fg_color="#f0f0f0")  # Set the background color of the application window

# Title Label
title = ctk.CTkLabel(
    app,
    text="Screen Time Tracker",
    font=("Arial", 36, "bold"),
    text_color="#333333"
    )

title.pack(pady=30)  # Pack the title label with some padding

# Status Label
status_label = ctk.CTkLabel(
    app,
    text="Ready",
    font=("Arial", 20, "bold"),
    text_color="#333333"
    )

status_label.pack(pady=10)  # Pack the status label with some padding

timer_label = ctk.CTkLabel(
    app,
    text="00:00:00",
    font=("Arial", 24, "bold"),
    text_color="#333333"
    )

timer_label.pack(pady=10)

# Buttons frame (this was missing before, which caused a NameError)
buttons_frame = ctk.CTkFrame(app, fg_color="transparent")
buttons_frame.pack(fill="x", padx=20)

# Buttons
# Let the 3 columns share the width equally
for col in range(4):
    buttons_frame.grid_columnconfigure(col, weight=1)

start_button = ctk.CTkButton(
    buttons_frame,
    text="Start Tracking",
    width=150,
    height=50,
    font=("Arial", 14, "bold"),
    command=start_tracking
    )

start_button.grid(
    row=0,
    column=0,
    padx=10,
    pady=10,
    sticky="ew"
    )  # Place the start button in the grid


stop_button = ctk.CTkButton(
    buttons_frame,
    text="Stop Tracking",
    width=150,
    height=50,
    font=("Arial", 14, "bold"),
    command=stop_tracking
    )

stop_button.grid(
    row=0,
    column=1,
    padx=10,
    pady=10,
    sticky="ew"
    )


chart_button = ctk.CTkButton(
    buttons_frame,
    text="View Chart",
    width=150,
    height=50,
    font=("Arial", 14, "bold"),
    command=show_chart
    )

chart_button.grid(
    row=0,
    column=2,
    padx=10,
    pady=10,
    sticky="ew"
    )


export_button = ctk.CTkButton(
    buttons_frame,
    text="Export CSV Data",
    width=150,
    height=50,
    font=("Arial", 14, "bold"),
    command=export_data
    )

export_button.grid(
    row=0,
    column=3,
    padx=10,
    pady=10,
    sticky="ew"
    )


# Theme
PRIMARY_COLOR = "#4a90e2"
HOVER_COLOR = "#357ABD"

for btn in [start_button, stop_button, chart_button, export_button]:
    btn.configure(
        fg_color=PRIMARY_COLOR,
        hover_color=HOVER_COLOR,
        text_color="white"
        )  # Set the foreground and hover colors for the buttons


# Total Time
total_time_label = ctk.CTkLabel(
    app,
    text="Total Time: 00:00:00",
    font=("Arial", 20, "bold"),
    text_color="#333333"
    )

total_time_label.pack(pady=10)


# App Usage Frame
app_usage_frame = ctk.CTkLabel(
    app,
    text="No data available",
    width=400,          # now just a minimum size
    height=200,         # now just a minimum size
    fg_color="#e4e4e4",
    text_color="#333333",
    anchor="nw",
    justify="left",
    font=("Consolas", 20),  # monospaced so the columns line up
    corner_radius=20
    )

app_usage_frame.pack(pady=20, padx=20, fill="both", expand=True)

# Keep text wrapped to the label width when the window is resized
_last_wrap = {"value": 0}


def _update_wrap(event):
    new_wrap = max(event.width - 40, 100)
    if new_wrap != _last_wrap["value"]:  # avoids a configure/resize loop
        _last_wrap["value"] = new_wrap
        app_usage_frame.configure(wraplength=new_wrap)


app_usage_frame.bind("<Configure>", _update_wrap)


def on_close():
    # Save any running session and close cleanly
    if tracking:
        stop_tracking()
    conn.close()
    app.destroy()


app.protocol("WM_DELETE_WINDOW", on_close)

app.mainloop()  # Start the main event loop of the application