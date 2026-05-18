# ============================================
# SkillBridge - Main Flask Application
# File: app.py
# ============================================

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from models import SkillGapAnalyzer, PlacementPredictor
from parsers import ResumeParser

# ============================================
# App Configuration
# ============================================
app = Flask(__name__)
app.secret_key = 'skillbridge_secret_2024_veltech'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Teja@nov22'
app.config['MYSQL_DB'] = 'skillbridge_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# File Upload Configuration
app.config['UPLOAD_FOLDER'] = 'uploads/resumes'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

mysql = MySQL(app)

# ============================================
# Helper Functions
# ============================================
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ROUTE 1: Home Page
# ============================================
@app.route('/')
def index():
    return render_template('index.html')

# ============================================
# ROUTE 2: Register
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'student')

        # Hash password for security
        hashed_password = generate_password_hash(password)

        cursor = mysql.connection.cursor()
        try:
            # Check if email already exists
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s", 
                (email,)
            )
            existing = cursor.fetchone()
            
            if existing:
                flash('Email already registered!', 'danger')
                return redirect(url_for('register'))

            # Insert new user
            cursor.execute(
                """INSERT INTO users 
                   (full_name, email, password_hash, role) 
                   VALUES (%s, %s, %s, %s)""",
                (full_name, email, hashed_password, role)
            )
            mysql.connection.commit()
            user_id = cursor.lastrowid

            # If student, create profile entry
            if role == 'student':
                roll_number = request.form['roll_number']
                department = request.form['department']
                cursor.execute(
                    """INSERT INTO student_profiles 
                       (user_id, roll_number, department) 
                       VALUES (%s, %s, %s)""",
                    (user_id, roll_number, department)
                )
                mysql.connection.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()

    return render_template('register.html')

# ============================================
# ROUTE 3: Login
# ============================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = %s AND is_active = TRUE",
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['email'] = user['email']

            # Update last login
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE users SET last_login = %s WHERE user_id = %s",
                (datetime.now(), user['user_id'])
            )
            mysql.connection.commit()
            cursor.close()

            flash(f'Welcome back, {user["full_name"]}!', 'success')

            if user['role'] == 'admin' or user['role'] == 'placement_officer':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')

# ============================================
# ROUTE 4: Logout
# ============================================
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

# ============================================
# ROUTE 5: Student Dashboard
# ============================================
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    cursor = mysql.connection.cursor()

    # Get student profile
    cursor.execute(
        """SELECT sp.*, u.full_name, u.email 
           FROM student_profiles sp
           JOIN users u ON sp.user_id = u.user_id
           WHERE sp.user_id = %s""",
        (session['user_id'],)
    )
    profile = cursor.fetchone()

    if not profile:
        flash('Please complete your profile first', 'warning')
        return redirect(url_for('update_profile'))

    # Get student skills
    cursor.execute(
        """SELECT sm.skill_name, sm.category, ss.proficiency_level
           FROM student_skills ss
           JOIN skills_master sm ON ss.skill_id = sm.skill_id
           WHERE ss.student_id = %s""",
        (profile['profile_id'],)
    )
    skills = cursor.fetchall()

    # Get top job recommendations
    cursor.execute(
        """SELECT r.match_percentage, r.missing_skills,
                  j.job_title, j.salary_lpa, c.company_name
           FROM recommendations r
           JOIN jobs j ON r.job_id = j.job_id
           JOIN companies c ON j.company_id = c.company_id
           WHERE r.student_id = %s
           ORDER BY r.match_percentage DESC LIMIT 5""",
        (profile['profile_id'],)
    )
    recommendations = cursor.fetchall()

    # Get test results
    cursor.execute(
        """SELECT test_name, score_percentage, test_category, taken_on
           FROM test_results
           WHERE student_id = %s
           ORDER BY taken_on DESC LIMIT 5""",
        (profile['profile_id'],)
    )
    test_results = cursor.fetchall()

    # Get unread notifications
    cursor.execute(
        """SELECT title, message, notif_type, created_at
           FROM notifications
           WHERE user_id = %s AND is_read = FALSE
           ORDER BY created_at DESC""",
        (session['user_id'],)
    )
    notifications = cursor.fetchall()
    cursor.close()

    return render_template(
        'student_dashboard.html',
        profile=profile,
        skills=skills,
        recommendations=recommendations,
        test_results=test_results,
        notifications=notifications
    )

# ============================================
# ROUTE 6: Upload & Parse Resume (AI Feature)
# ============================================
@app.route('/student/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('student_dashboard'))

    file = request.files['resume']

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{session['user_id']}_{timestamp}_{filename}"

        # Create upload folder if it does not exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        # Parse resume using AI
        parser = ResumeParser()
        parsed_data = parser.parse_resume(file_path)

        # Get student profile ID
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT profile_id FROM student_profiles WHERE user_id = %s",
            (session['user_id'],)
        )
        profile = cursor.fetchone()
        profile_id = profile['profile_id']

        # Save resume data to DB
        cursor.execute(
            """INSERT INTO resumes 
               (student_id, file_name, file_path, parsed_skills, ats_score)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                profile_id,
                unique_filename,
                file_path,
                json.dumps(parsed_data['skills']),
                parsed_data['ats_score']
            )
        )
        mysql.connection.commit()

        # Auto-add extracted skills to student profile
        for skill_name in parsed_data['skills']:
            cursor.execute(
                "SELECT skill_id FROM skills_master WHERE skill_name = %s",
                (skill_name,)
            )
            skill = cursor.fetchone()

            if skill:
                try:
                    cursor.execute(
                        """INSERT IGNORE INTO student_skills 
                           (student_id, skill_id, proficiency_level)
                           VALUES (%s, %s, %s)""",
                        (profile_id, skill['skill_id'], 'intermediate')
                    )
                    mysql.connection.commit()
                except:
                    pass

        cursor.close()

        # Trigger AI recommendation generation
        generate_recommendations(profile_id)

        flash(
            f'Resume uploaded! Found {len(parsed_data["skills"])} skills. '
            f'ATS Score: {parsed_data["ats_score"]}%',
            'success'
        )
    else:
        flash('Only PDF and DOCX files are allowed', 'danger')

    return redirect(url_for('student_dashboard'))

# ============================================
# ROUTE 7: Generate AI Recommendations
# ============================================
def generate_recommendations(profile_id):
    cursor = mysql.connection.cursor()

    # Get student skills
    cursor.execute(
        """SELECT sm.skill_name
           FROM student_skills ss
           JOIN skills_master sm ON ss.skill_id = sm.skill_id
           WHERE ss.student_id = %s""",
        (profile_id,)
    )
    student_skills_raw = cursor.fetchall()
    student_skills = [s['skill_name'].lower() for s in student_skills_raw]

    # Get student CGPA
    cursor.execute(
        "SELECT cgpa, backlogs FROM student_profiles WHERE profile_id = %s",
        (profile_id,)
    )
    student_data = cursor.fetchone()
    cgpa = float(student_data['cgpa']) if student_data['cgpa'] else 0
    backlogs = student_data['backlogs'] or 0

    # Get all active jobs
    cursor.execute(
        """SELECT j.*, c.company_name
           FROM jobs j
           JOIN companies c ON j.company_id = c.company_id
           WHERE j.is_active = TRUE 
           AND j.min_cgpa <= %s
           AND j.max_backlogs >= %s""",
        (cgpa, backlogs)
    )
    jobs = cursor.fetchall()

    # Initialize AI analyzer
    analyzer = SkillGapAnalyzer()

    # Clear old recommendations
    cursor.execute(
        "DELETE FROM recommendations WHERE student_id = %s",
        (profile_id,)
    )

    # Analyze each job
    for job in jobs:
        required_skills = [
            s.strip().lower() 
            for s in job['required_skills'].split(',')
        ]

        analysis = analyzer.analyze_gap(student_skills, required_skills)

        # Save recommendation
        cursor.execute(
            """INSERT INTO recommendations
               (student_id, job_id, match_percentage, 
                missing_skills, recommendation_type)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                profile_id,
                job['job_id'],
                analysis['match_percentage'],
                json.dumps(analysis['missing_skills']),
                'job'
            )
        )

    mysql.connection.commit()

    # Update placement readiness score
    predictor = PlacementPredictor()
    readiness = predictor.predict_readiness(
        cgpa=cgpa,
        skills_count=len(student_skills),
        backlogs=backlogs
    )

    cursor.execute(
        """UPDATE student_profiles 
           SET readiness_score = %s 
           WHERE profile_id = %s""",
        (readiness, profile_id)
    )
    mysql.connection.commit()
    cursor.close()

# ============================================
# ROUTE 8: Skill Gap Analysis API
# ============================================
@app.route('/api/skill-gap', methods=['POST'])
@login_required
def api_skill_gap():
    data = request.get_json()
    student_skills = data.get('student_skills', [])
    job_id = data.get('job_id')

    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT required_skills, job_title FROM jobs WHERE job_id = %s",
        (job_id,)
    )
    job = cursor.fetchone()
    cursor.close()

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    required_skills = [
        s.strip().lower() 
        for s in job['required_skills'].split(',')
    ]

    analyzer = SkillGapAnalyzer()
    result = analyzer.analyze_gap(
        [s.lower() for s in student_skills],
        required_skills
    )

    return jsonify({
        'job_title': job['job_title'],
        'match_percentage': result['match_percentage'],
        'matched_skills': result['matched_skills'],
        'missing_skills': result['missing_skills'],
        'message': result['message']
    })

# ============================================
# ROUTE 9: Admin Dashboard
# ============================================
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session['role'] not in ['admin', 'placement_officer']:
        flash('Access denied!', 'danger')
        return redirect(url_for('student_dashboard'))

    cursor = mysql.connection.cursor()

    # Total students count
    cursor.execute(
        "SELECT COUNT(*) as total FROM student_profiles"
    )
    total_students = cursor.fetchone()['total']

    # Placement status breakdown
    cursor.execute(
        """SELECT placement_status, COUNT(*) as count 
           FROM student_profiles 
           GROUP BY placement_status"""
    )
    placement_stats = cursor.fetchall()

    # Department-wise stats
    cursor.execute(
        """SELECT department,
                  COUNT(*) as total,
                  AVG(cgpa) as avg_cgpa,
                  SUM(placement_status='placed') as placed
           FROM student_profiles
           GROUP BY department"""
    )
    dept_stats = cursor.fetchall()

    # Recent companies
    cursor.execute(
        "SELECT * FROM companies ORDER BY added_on DESC LIMIT 5"
    )
    recent_companies = cursor.fetchall()

    # Top performing students
    cursor.execute(
        """SELECT u.full_name, sp.cgpa, sp.department, 
                  sp.readiness_score, sp.placement_status
           FROM student_profiles sp
           JOIN users u ON sp.user_id = u.user_id
           ORDER BY sp.readiness_score DESC LIMIT 10"""
    )
    top_students = cursor.fetchall()

    cursor.close()

    return render_template(
        'admin_dashboard.html',
        total_students=total_students,
        placement_stats=placement_stats,
        dept_stats=dept_stats,
        recent_companies=recent_companies,
        top_students=top_students
    )

# ============================================
# ROUTE 10: Get All Jobs (API for Android)
# ============================================
@app.route('/api/jobs', methods=['GET'])
def api_get_jobs():
    cursor = mysql.connection.cursor()
    cursor.execute(
        """SELECT j.*, c.company_name, c.company_type
           FROM jobs j
           JOIN companies c ON j.company_id = c.company_id
           WHERE j.is_active = TRUE
           ORDER BY j.posted_on DESC"""
    )
    jobs = cursor.fetchall()
    cursor.close()

    # Convert to JSON serializable
    for job in jobs:
        if job.get('posted_on'):
            job['posted_on'] = str(job['posted_on'])
        if job.get('application_deadline'):
            job['application_deadline'] = str(job['application_deadline'])

    return jsonify({'jobs': jobs, 'total': len(jobs)})

# ============================================
# Run Application
# ============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)