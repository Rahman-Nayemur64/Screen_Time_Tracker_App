import matplotlib.pyplot as plt 
import pandas as pd
import customtkinter as ctk  # Build entire Graphical User Interface 
import sqlite3 
import threading # for multitasking support
import time # for time tracking
import psutil # for system monitoring
import win32gui  # for window management
import win32process  # for process management

from datetime import datetime # for date and time management
import tkinter as tk
from tkinter import messagebox  # for displaying message boxes

# Database 
conn = sqlite3.connect('screen_time.db')
cursor = conn.cursor() # Create a table to store screen time database
cursor.execute('''                                
    CREATE TABLE IF NOT EXISTS usage  (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT,
        usage_seconds INTEGER,
        date TEXT
    )
''')

conn.commit() # Commit save changes to the database


# Tracker
tracking = False # Flag to track if tracking is active
usage_data = {} # Dictionary to store usage data
session_seconds = 0 # Variable to track session time in seconds

def get_active_app():
    try:
        hwnd = win32gui.GetForegroundWindow() # Get the handle of the active window
        _, pid = win32process.GetWindowThreadProcessId(hwnd) # Get the process ID
        process = psutil.Process(pid) # Get the process information
        return process.name() # Return the name of the active application
    except:
        return "Unknown" # Return "Unknown" if unable to get the active application

def traking_loop():
    global tracking, session_seconds, usage_data
    while tracking:
        active_app = get_active_app() # Get the active application
        usage_data[active_app] = usage_data.get(active_app, 0) + 1 # Increment usage time for the active application
        update_dashboard() # Update the dashboard with the latest usage data
        if active_app in usage_data:
            usage_data[active_app] += 1 # Increment usage time for the active application
        else:
            usage_data[active_app] = 1 # Initialize usage time for the new application
        time.sleep(1) # Wait for 1 second before checking again
        
# Database Storage
def save_to_database():
    today = datetime.now().strftime("%Y-%m-%d") # Get the current date
    for app_name, usage_seconds in usage_data.items():
        cursor.execute('''
            INSERT INTO usage (
                app_name, 
                usage_seconds, 
                date)
            VALUES (?, ?, ?)
        ''', (app_name, usage_seconds, today)) # Insert usage data into the database
        conn.commit() # Commit save changes to the database

def update_dashboard():
    total_seconds = sum(usage_data.values()) # Calculate total usage time
    hours = total_seconds // 3600 
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    total_time_label.configure(
        text=f"Total Time: {hours:02}:{minutes:02}:{seconds:02}"
        ) # Update the total time label
    
    sorted_apps = sorted(
        usage_data.items(), 
        key=lambda x: x[1], 
        reverse=True
        ) # Sort the applications by usage time in descending order
    
    text = ""
    
    for app, sec in sorted_apps[:5]:  # Limit to top 5 applications
        hours = sec // 3600
        minutes = (sec % 3600) // 60
        seconds = sec % 60
        text += (
            f"{app:<20}"
            f"{hours:02}:{minutes:02}:{seconds:02}\n")
    
    app_usage_frame.configure(
        text=text
        ) # Update the application usage frame 

def update_live_timer():
    
    if tracking:
        global session_seconds
        session_seconds += 1 
        
        hours = session_seconds // 3600 
        minutes = (session_seconds % 3600) // 60
        seconds = session_seconds % 60
        
        timer_label.configure(
            text=f"{hours:02}:{minutes:02}:{seconds:02}"
            ) # 02 means always show 2 digits, even if the number is less than 10
        app.after(1000, update_live_timer) # Schedule the next update after 1 second
    

def start_tracking():
    global tracking, session_seconds, usage_data
    
    if tracking:
        return  # If tracking is already active, do nothing
    
    tracking = True # Set tracking flag to True
    session_seconds = 0 # Reset session time
    usage_data = {} # Reset usage data
    status_label.configure(text="Tracking...") # Update status label
    update_live_timer() 
    threading.Thread(
        target=traking_loop,
        daemon=True
        ).start() # Start the tracking loop in a separate thread

def stop_tracking():
    global tracking
    tracking = False
    timer_label.configure(text="00:00:00") # Reset the timer label
    save_to_database() # Save the usage data to the database
    status_label.configure(text="Tracking stopped.") # Update status label

def show_chart():
      if not usage_data:
          messagebox.showwarning(
              "No Data", 
              "Track some apps before viewing the chart."
              )
          return
      apps = list(usage_data.keys())
      seconds = list(usage_data.values())
      
      plt.figure(figsize=(10, 6))
      plt.pie(
          seconds, 
          labels=apps,
          autopct='%1.1f%%'
        )
      
      plt.title("App Usage Distribution")
      plt.show() # Display the pie chart
      
      
def export_data():
    if not usage_data:
        messagebox.showwarning(
            "No Data", 
            "Track some apps before exporting data."
            )
        return
    
    df = pd.DataFrame(
        
        {
            "Application": usage_data.keys(),
            "Seconds used": usage_data.values()
        }
        ) # Create a DataFrame from the usage data
    
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
app.geometry("800x600")  #
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
    text = "00:00:00",
    font = ("Arial", 24, "bold"),
    text_color = "#333333"
    )

timer_label.pack(pady=10)  

# Buttons Frame
buttons_frame = ctk.CTkFrame(
    app,
    fg_color="#f0f0f0",
    corner_radius=15
    )  

buttons_frame.pack(pady=20)  


# Buttons
start_button = ctk.CTkButton(
    buttons_frame,
    text="Start Tracking",
    width=200,
    height=50,
    font=("Arial", 16, "bold"),
    command= start_tracking
    )  

start_button.grid(
    row=0, 
    column=0, 
    padx=20, 
    pady=10
    )  # Place the start button in the grid


stop_button = ctk.CTkButton(
    buttons_frame,
    text="Stop Tracking",
    width=200,
    height=50,
    font=("Arial", 16, "bold"),
    command= stop_tracking
    )

stop_button.grid(
    row=0,
    column=1,
    padx=20,
    pady=10
)


chart_button = ctk.CTkButton(
    buttons_frame,
    text="View Chart",
    width=200,
    height=50,
    font=("Arial", 16, "bold"),
    command= show_chart
    )

chart_button.grid(
    row=0,
    column=2,
    padx=20,    
    pady=10
    )


export_button = ctk.CTkButton(
    buttons_frame,
    text="Export CSV Data",
    width=200,
    height=50,
    font=("Arial", 16, "bold"),
    command=export_data
    )

export_button.grid(
    row=1,
    column=0,
    padx=20,
    pady=10
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
    width=800,
    height=600,
    fg_color="#f0f0f0",
    text_color="#333333",
    anchor="nw",
    justify="left",
    font=("Arial", 20),
    corner_radius=20
    )

app_usage_frame.pack(pady=20)  

app.mainloop()  # Start the main event loop of the application



