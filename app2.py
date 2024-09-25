from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import csv
import os
from datetime import datetime, time, timedelta
import pytz
import pandas as pd  # For exporting to Excel

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for flashing messages and sessions

# Define your local time zone
LOCAL_TIME_ZONE = pytz.timezone('Asia/Karachi')

# Configurable shift times
SHIFT_START = time(6, 0)       # 6:00 AM
SHIFT_END = time(11, 59)       # 11:59 AM
EXPECTED_TIME_IN = time(8, 0)  # 8:00 AM

# PM Shift times
PM_SHIFT_START = time(18, 0)   # 6:00 PM
PM_SHIFT_END = time(23, 59)    # 11:59 PM
PM_EXPECTED_TIME_IN = time(20, 0)  # 8:00 PM

MASTER_KEY = 'pangzpogi'  # Master key for accessing the report

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    # Get the name and group from the form
    name = request.form['name']
    group = request.form['group']
    action = request.form['action']
    
    # Get current time in local time zone
    timestamp = datetime.now(LOCAL_TIME_ZONE)
    
    # Separate date and time
    date_str = timestamp.strftime('%Y-%m-%d')
    time_str = timestamp.strftime('%H:%M:%S')
    
    print("Current server time:", f"{date_str} {time_str}")  # For debugging

    lateness_duration = ''  # Initialize lateness_duration

    if action == 'time_in':
        current_time = timestamp.time()

        # Check if current time is within the AM shift window
        if SHIFT_START <= current_time <= SHIFT_END:
            # Create a naive datetime for expected_time
            expected_time_naive = datetime.combine(timestamp.date(), EXPECTED_TIME_IN)
            # Localize expected_time to make it timezone-aware
            expected_time = LOCAL_TIME_ZONE.localize(expected_time_naive)
            shift = 'AM Shift'

        # Check if current time is within the PM shift window
        elif PM_SHIFT_START <= current_time <= PM_SHIFT_END:
            expected_time_naive = datetime.combine(timestamp.date(), PM_EXPECTED_TIME_IN)
            expected_time = LOCAL_TIME_ZONE.localize(expected_time_naive)
            shift = 'PM Shift'
        else:
            expected_time = None
            shift = 'Unknown'

        if expected_time:
            # Check if late
            if timestamp > expected_time:
                status = 'Late'
                # Calculate duration of lateness
                lateness_duration_td = timestamp - expected_time
                # Convert to minutes
                lateness_minutes = int(lateness_duration_td.total_seconds() // 60)
                lateness_duration = f'{lateness_minutes} minutes'
            else:
                status = 'On Time'
                lateness_duration = ''
        else:
            status = 'Invalid Time-In'
            lateness_duration = ''
    else:
        status = ''
        shift = ''
        lateness_duration = ''

    # Prepare the data to be written to CSV
    data = [name, group, action, date_str, time_str, status, shift, lateness_duration]

    # Write data to CSV
    file_exists = os.path.isfile('log.csv')

    with open('log.csv', 'a', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile, quoting=csv.QUOTE_ALL)  # Use quoting to preserve strings
        if not file_exists:
            csvwriter.writerow(['Name', 'Group', 'Action', 'Date', 'Time', 'Status', 'Shift', 'Lateness Duration'])
        csvwriter.writerow(data)

    # Flash a success message using the name
    if action == 'time_in':
        if status == 'Invalid Time-In':
            flash_msg = f"{status}. Please clock in during your shift hours."
        elif status == 'Late':
            flash_msg = f"{status}! You are {lateness_duration} late. Time-In recorded for {name} on {date_str} at {time_str}"
        else:
            flash_msg = f"{status}! Time-In recorded for {name} on {date_str} at {time_str}"
    else:
        flash_msg = f"Time-Out recorded for {name} on {date_str} at {time_str}"

    flash(flash_msg)

    return redirect(url_for('index'))

# The rest of your existing routes (login, report, export, logout) remain the same.

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        master_key = request.form['master_key']
        if master_key == MASTER_KEY:
            session['authenticated'] = True
            return redirect(url_for('report'))
        else:
            flash('Invalid master key. Access denied.')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/report')
def report():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    # Read the CSV file and pass the data to the template
    if os.path.isfile('log.csv'):
        with open('log.csv', 'r', newline='', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile)
            data = list(csvreader)
    else:
        data = []

    return render_template('report.html', data=data)

@app.route('/export')
def export():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    # Check if the CSV file exists
    if os.path.isfile('log.csv'):
        # Read the CSV file using pandas
        df = pd.read_csv('log.csv', encoding='utf-8')
        # Save it as an Excel file
        excel_file = 'attendance_report.xlsx'
        df.to_excel(excel_file, index=False)
        # Send the file to the user
        return send_file(excel_file, as_attachment=True)
    else:
        flash('No attendance data available to export.')
        return redirect(url_for('report'))

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    flash('You have been logged out.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=8003)
