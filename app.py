import os
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db, DATABASE
from io import BytesIO

app = Flask(__name__, 
            template_folder='.',
            static_folder='static',
            static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123') # fallback for local dev

# Initialize Database
if not os.path.exists(DATABASE):
    init_db()

# --- Helper Functions ---
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

# Index / Home
@app.route('/')
def index():
    return render_template('index.html')

# Serve root assets fallbacks
@app.route('/style.css')
def serve_css():
    for path in [os.path.join(app.root_path, 'static', 'css', 'style.css'), 
                 os.path.join(app.root_path, 'style.css')]:
        if os.path.exists(path):
            return send_file(path, mimetype='text/css')
    return "Not Found", 404

@app.route('/script.js')
def serve_js():
    for path in [os.path.join(app.root_path, 'static', 'js', 'script.js'), 
                 os.path.join(app.root_path, 'script.js')]:
        if os.path.exists(path):
            return send_file(path, mimetype='application/javascript')
    return "Not Found", 404

@app.route('/favicon.ico')
def favicon():
    icon_path = os.path.join(app.root_path, 'favicon.ico')
    if os.path.exists(icon_path):
        return send_file(icon_path, mimetype='image/x-icon')
    return '', 204

# Authentication: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'error')
        finally:
            conn.close()
            
    return render_template('register.html')

# Authentication: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            
    return render_template('login.html')

# Authentication: Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    conn = get_db_connection()
    students_data = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    
    # Calculate stats
    total_students = len(set([s['roll_number'] for s in students_data]))
    total_records = len(students_data)
    
    if total_records > 0:
        avg_marks = sum(s['marks'] for s in students_data) / total_records
        avg_attendance = sum(s['attendance'] for s in students_data) / total_records
        
        # Subject averages
        df = pd.DataFrame([dict(s) for s in students_data])
        subject_avg = df.groupby('subject')['marks'].mean().to_dict()
        
        # Top and Low performers (by average marks)
        student_avg = df.groupby('name')['marks'].mean().sort_values(ascending=False)
        top_performers = student_avg.head(5).to_dict()
        low_performers = student_avg.tail(5).to_dict()
    else:
        avg_marks = 0
        avg_attendance = 0
        subject_avg = {}
        top_performers = {}
        low_performers = {}

    return render_template('dashboard.html', 
                           total_students=total_students,
                           avg_marks=round(avg_marks, 2),
                           avg_attendance=round(avg_attendance, 2),
                           subject_avg=subject_avg,
                           top_performers=top_performers,
                           low_performers=low_performers)

# Student Management
@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        attendance = int(request.form['attendance'])
        
        subjects = ['Mathematics', 'Physics', 'Chemistry', 'Biology', 'English']
        records_added = 0
        
        for sub in subjects:
            mark_key = f'marks_{sub}'
            if mark_key in request.form and request.form[mark_key]:
                marks = int(request.form[mark_key])
                conn.execute('INSERT INTO students (name, roll_number, subject, marks, attendance, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                             (name, roll_number, sub, marks, attendance, session.get('user_id', 0)))
                records_added += 1
        
        conn.commit()
        if records_added > 0:
            flash(f'Profile for {name} submitted successfully ({records_added} subjects).', 'success')
        else:
            flash('No marks were entered. Record not created.', 'warning')
        return redirect(url_for('students'))

    # Fetch records with filtering and sorting
    user_id = session.get('user_id')
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'name')
    
    # Safe sorting handling
    allowed_sorts = ['name', 'roll_number', 'subject', 'marks', 'attendance', 'marks DESC', 'attendance DESC']
    if sort_by not in allowed_sorts:
        sort_by = 'name'
    
    query = 'SELECT * FROM students WHERE user_id = ?'
    params = [user_id]
    
    if search:
        query += ' AND (name LIKE ? OR roll_number LIKE ? OR subject LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    
    query += f' ORDER BY {sort_by}'
    
    students_list = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('students.html', students=students_list, search=search)

# Edit Record
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    user_id = session.get('user_id')
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ? AND user_id = ?', (id, user_id)).fetchone()
    
    if not student:
        conn.close()
        flash('Student record not found.', 'danger')
        return redirect(url_for('students'))

    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        subject = request.form['subject']
        marks = int(request.form['marks'])
        attendance = int(request.form['attendance'])
        
        conn.execute('UPDATE students SET name=?, roll_number=?, subject=?, marks=?, attendance=? WHERE id=?',
                     (name, roll_number, subject, marks, attendance, id))
        conn.commit()
        conn.close()
        flash('Record updated successfully.', 'success')
        return redirect(url_for('students'))
        
    conn.close()
    return render_template('edit_student.html', student=student)

# Delete Record
@app.route('/delete/<int:id>')
@login_required
def delete_student(id):
    user_id = session.get('user_id')
    conn = get_db_connection()
    conn.execute('DELETE FROM students WHERE id = ? AND user_id = ?', (id, user_id))
    conn.commit()
    conn.close()
    flash('Record deleted successfully.', 'success')
    return redirect(url_for('students'))

# Analytics Data API
@app.route('/api/analytics')
@login_required
def analytics_data():
    try:
        user_id = session.get('user_id')
        conn = get_db_connection()
        students_data = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        
        if not students_data:
            return {'status': 'empty'}
            
        df = pd.DataFrame([dict(s) for s in students_data])
        
        # Ensure marks and attendance are numeric
        df['marks'] = pd.to_numeric(df['marks'], errors='coerce')
        df['attendance'] = pd.to_numeric(df['attendance'], errors='coerce')
        df = df.dropna(subset=['marks', 'attendance'])
        
        if df.empty:
            return {'status': 'empty'}

        # Subject-wise marks
        subj_avg = df.groupby('subject')['marks'].mean().to_dict()
        # Convert NumPy types to plain Python types
        subjects = list(subj_avg.keys())
        averages = [round(float(v), 2) for v in subj_avg.values()]
        
        # Marks distribution
        bins = [0, 40, 60, 80, 100]
        labels = ['Fail', 'Average', 'Good', 'Excellent']
        df['category'] = pd.cut(df['marks'], bins=bins, labels=labels, include_lowest=True)
        dist_counts = df['category'].value_counts().reindex(labels, fill_value=0).to_dict()
        # Convert values to plain int
        final_dist = {str(k): int(v) for k, v in dist_counts.items()}
        
        # Attendance vs Marks
        # Limit records to avoid massive JS payloads, but for small school apps this is fine
        correlation = []
        for _, row in df.iterrows():
            correlation.append({
                'attendance': float(row['attendance']),
                'marks': float(row['marks'])
            })
        
        return {
            'status': 'success',
            'subjects': subjects,
            'subject_averages': averages,
            'distribution': final_dist,
            'attendance_marks': correlation
        }
    except Exception as e:
        print(f"Analytics Error: {str(e)}")
        return {'status': 'error', 'message': str(e)}, 200 # Return 200 with error status to prevent browser console 500s

# Export CSV
@app.route('/export')
@login_required
def export_csv():
    user_id = session.get('user_id')
    conn = get_db_connection()
    students_data = conn.execute('SELECT name, roll_number, subject, marks, attendance FROM students WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    
    df = pd.DataFrame([dict(s) for s in students_data])
    
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='student_report.csv')

# Leaderboard
@app.route('/leaderboard')
@login_required
def leaderboard():
    user_id = session.get('user_id')
    conn = get_db_connection()
    # Leaderboard can show all students or just user's? 
    # Usually a leaderboard shows all, but if it's private educators, maybe only theirs.
    # The prompt implies a collaborative environment? "Empower educators".
    # I'll keep it global but add names of subjects or something.
    students_data = conn.execute('SELECT * FROM students').fetchall()
    conn.close()
    
    if not students_data:
        return render_template('leaderboard.html', rankings=[])
        
    df = pd.DataFrame([dict(s) for s in students_data])
    rankings = df.groupby(['name', 'roll_number'])[['marks', 'attendance']].mean().reset_index()
    rankings = rankings.sort_values(by='marks', ascending=False)
    
    return render_template('leaderboard.html', rankings=rankings.to_dict(orient='records'))

# About Page
@app.route('/about')
@login_required
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
