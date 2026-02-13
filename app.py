import os
import sqlite3
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db, DATABASE
from io import BytesIO
from functools import wraps

app = Flask(__name__, 
            template_folder='.',
            static_folder='static',
            static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-123-change-this-in-production')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Initialize Database
if not os.path.exists(DATABASE):
    init_db()

# --- Helper Functions ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def validate_marks(marks):
    """Validate marks between 0-100"""
    try:
        marks = int(marks)
        return 0 <= marks <= 100, marks
    except:
        return False, 0

def validate_attendance(attendance):
    """Validate attendance between 0-100"""
    try:
        attendance = int(attendance)
        return 0 <= attendance <= 100, attendance
    except:
        return False, 0

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
        username = request.form['username'].strip()
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                        (username, hashed_password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose another.', 'error')
        finally:
            conn.close()
            
    return render_template('register.html')

# Authentication: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True
            flash(f'Welcome back, {user["username"]}!', 'success')
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
    if students_data:
        df = pd.DataFrame([dict(s) for s in students_data])
        
        # Ensure marks and attendance are numeric
        df['marks'] = pd.to_numeric(df['marks'], errors='coerce')
        df['attendance'] = pd.to_numeric(df['attendance'], errors='coerce')
        
        total_students = len(df['roll_number'].unique())
        total_records = len(students_data)
        avg_marks = df['marks'].mean()
        avg_attendance = df['attendance'].mean()
        
        # Subject averages (rounding and dropping NaNs)
        subject_avg = df.groupby('subject')['marks'].mean().dropna().round(2).to_dict()
        
        # Top and Low performers (by average marks) - Group by both name and roll_number
        student_performance = df.groupby(['name', 'roll_number'])['marks'].mean().dropna().sort_values(ascending=False).reset_index()
        top_performers = student_performance.head(5).to_dict(orient='records')
        low_performers = student_performance.tail(5).sort_values('marks').to_dict(orient='records')
    else:
        total_students = 0
        total_records = 0
        avg_marks = 0
        avg_attendance = 0
        subject_avg = {}
        top_performers = []
        low_performers = []

    return render_template('dashboard.html', 
                           total_students=total_students,
                           avg_marks=round(float(avg_marks), 2) if not pd.isna(avg_marks) else 0,
                           avg_attendance=round(float(avg_attendance), 2) if not pd.isna(avg_attendance) else 0,
                           subject_avg=subject_avg,
                           top_performers=top_performers,
                           low_performers=low_performers)

# Student Management
@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    conn = get_db_connection()
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        roll_number = request.form['roll_number'].strip().upper()
        
        # Validate attendance
        is_valid_att, attendance = validate_attendance(request.form['attendance'])
        if not is_valid_att:
            conn.close()
            flash('Attendance must be between 0-100.', 'error')
            return redirect(url_for('students'))
        
        subjects = ['Mathematics', 'Physics', 'Chemistry', 'Biology', 'English']
        records_added = 0
        
        for sub in subjects:
            mark_key = f'marks_{sub}'
            if mark_key in request.form and request.form[mark_key].strip():
                is_valid_marks, marks = validate_marks(request.form[mark_key])
                if is_valid_marks:
                    conn.execute('''INSERT INTO students 
                                   (name, roll_number, subject, marks, attendance, user_id) 
                                   VALUES (?, ?, ?, ?, ?, ?)''',
                                 (name, roll_number, sub, marks, attendance, user_id))
                    records_added += 1
        
        conn.commit()
        conn.close()
        if records_added > 0:
            flash(f'Profile for {name} submitted successfully ({records_added} subjects).', 'success')
        else:
            flash('No valid marks were entered. Record not created.', 'warning')
        return redirect(url_for('students'))

    # Fetch records with filtering and sorting
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'name')
    
    # Safe sorting handling
    allowed_sorts = ['name', 'roll_number', 'subject', 'marks', 'attendance', 
                    'marks DESC', 'attendance DESC', 'name DESC', 'roll_number DESC']
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
        flash('Student record not found.', 'error')
        return redirect(url_for('students'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        roll_number = request.form['roll_number'].strip().upper()
        subject = request.form['subject']
        
        is_valid_marks, marks = validate_marks(request.form['marks'])
        is_valid_att, attendance = validate_attendance(request.form['attendance'])
        
        if not is_valid_marks or not is_valid_att:
            flash('Marks and attendance must be between 0-100.', 'error')
        else:
            conn.execute('''UPDATE students 
                           SET name=?, roll_number=?, subject=?, marks=?, attendance=? 
                           WHERE id=?''',
                         (name, roll_number, subject, marks, attendance, id))
            conn.commit()
            flash('Record updated successfully.', 'success')
            conn.close()
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
            return jsonify({'status': 'empty'})
            
        df = pd.DataFrame([dict(s) for s in students_data])
        
        # Ensure marks and attendance are numeric
        df['marks'] = pd.to_numeric(df['marks'], errors='coerce')
        df['attendance'] = pd.to_numeric(df['attendance'], errors='coerce')
        df = df.dropna(subset=['marks', 'attendance'])
        
        if df.empty:
            return jsonify({'status': 'empty'})

        # Helper function to sanitize for JSON
        def json_safe(val):
            if pd.isna(val) or val is None:
                return 0
            return float(val)

        # Subject-wise marks
        subj_avg = df.groupby('subject')['marks'].mean().dropna().to_dict()
        subjects = list(subj_avg.keys())
        averages = [round(json_safe(v), 2) for v in subj_avg.values()]
        
        # Marks distribution
        bins = [0, 40, 60, 80, 100]
        labels = ['Fail (0-39)', 'Average (40-59)', 'Good (60-79)', 'Excellent (80-100)']
        df['category'] = pd.cut(df['marks'], bins=bins, labels=labels, include_lowest=True)
        dist_counts = df['category'].value_counts().reindex(labels, fill_value=0).to_dict()
        final_dist = {str(k): int(v) for k, v in dist_counts.items()}
        
        # Attendance vs Marks
        correlation = []
        for _, row in df.iterrows():
            m = json_safe(row['marks'])
            a = json_safe(row['attendance'])
            correlation.append({'attendance': a, 'marks': m})
        
        return jsonify({
            'status': 'success',
            'subjects': subjects,
            'subject_averages': averages,
            'distribution': final_dist,
            'attendance_marks': correlation[:100]  # Limit to 100 points
        })
    except Exception as e:
        print(f"Analytics Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

# Export CSV
@app.route('/export')
@login_required
def export_csv():
    user_id = session.get('user_id')
    conn = get_db_connection()
    students_data = conn.execute('''SELECT name, roll_number, subject, marks, attendance, 
                                   datetime(created_at) as date_added 
                                   FROM students WHERE user_id = ?''', (user_id,)).fetchall()
    conn.close()
    
    if not students_data:
        flash('No data to export.', 'warning')
        return redirect(url_for('students'))
    
    df = pd.DataFrame([dict(s) for s in students_data])
    
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        output, 
        mimetype='text/csv', 
        as_attachment=True, 
        download_name=f'student_report_{session["username"]}.csv'
    )

# Leaderboard
@app.route('/leaderboard')
@login_required
def leaderboard():
    user_id = session.get('user_id')
    conn = get_db_connection()
    students_data = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    
    if not students_data:
        return render_template('leaderboard.html', rankings=[])
        
    df = pd.DataFrame([dict(s) for s in students_data])
    # Ensure numeric for proper aggregation
    df['marks'] = pd.to_numeric(df['marks'], errors='coerce')
    df['attendance'] = pd.to_numeric(df['attendance'], errors='coerce')
    
    rankings = df.groupby(['name', 'roll_number'])[['marks', 'attendance']].mean().dropna(subset=['marks']).reset_index()
    rankings = rankings.sort_values(by='marks', ascending=False)
    rankings['rank'] = range(1, len(rankings) + 1)
    
    return render_template('leaderboard.html', rankings=rankings.to_dict(orient='records'))

# About Page
@app.route('/about')
@login_required
def about():
    return render_template('about.html')

# Health check for Render
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)