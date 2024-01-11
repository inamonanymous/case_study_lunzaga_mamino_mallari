from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from sqlalchemy import and_, or_
from flask_migrate import Migrate
import qrcode
import os
from model.models import db, Student, Admin, Department
import csv
from datetime import date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///sqlite.db"
db.init_app(app)
QR_CODE_FOLDER = 'static/qrcodes'  # Folder to save QR code images
app.secret_key = "mamino_mallari_lunzaga"
migrate = Migrate(app, db)

def generate_file_name(dept_folder, year_folder, section_folder, current_date=date.today().strftime("%Y-%m-%d")):
    data_folder = os.path.join('attendance_data', dept_folder, year_folder, section_folder)
    os.makedirs(data_folder, exist_ok=True)

    return os.path.join(data_folder, f"attendance_at_{current_date}.csv")

@app.route('/logout', methods=['POST'])
def logout():
    if 'submit' in request.form:
        session.clear()
        return redirect(url_for('index'))
    return redirect(request.url)

@app.route('/delete-student/<string:student_number>', methods=['DELETE'])
def delete_student(student_number):
    if 'username' not in session:
        return redirect(url_for('index'))
    target_student = Student.query.filter_by(student_number=student_number).first()
    if not target_student:
        return jsonify({"message": "not found"}), 404
    db.session.delete(target_student)
    db.session.commit()
    return jsonify({"message": "deleted"}), 204

    
@app.route('/delete-department/<int:id>', methods=['DELETE'])
def delete_department(id):
    if 'username' not in session:
        return redirect(url_for('index'))
    target_department = Department.query.filter_by(id=id).first()
    if not target_department:
        return jsonify({"message": "not deleted"})    
    db.session.delete(target_department)
    db.session.commit()
    return jsonify({"message": "deleted"})

@app.route('/filter-departments', methods=['GET'])
def filter_departments():
    if 'username' in session:
        course = request.args.get("course")
        year = request.args.get("year")
        section = request.args.get("section")

        query = Department.query

        if course:
            query = query.filter(Department.course == str(course))

        if year:
            query = query.filter(Department.year == str(year))

        if section:
            query = query.filter(Department.section == str(section))

        departments = query.all()

        departments_list = [{
            'id': i.id,
            'course': i.course,
            'year': i.year,
            'section': i.section,
        } for i in departments]

        return jsonify(departments_list)

    return redirect(url_for('index'))

@app.route('/filter-students', methods=['GET'])
def filter_students():
    if 'username' in session:
        course = request.args.get("course")
        year = request.args.get("year")
        section = request.args.get("section")

        query = db.session.query(
            Student.firstname,
            Student.surname,
            Student.student_number,
            Department.course,
            Department.year,
            Department.section,
            Student.qrcode
        ).join(Department, and_(Student.department == Department.id))

        if course:
            query = query.filter(Department.course == str(course))

        if year:
            query = query.filter(Department.year == str(year))

        if section:
            query = query.filter(Department.section == str(section))


        students = query.all()

        students_list = [{
            'student_firstname': i.firstname,
            'student_surname': i.surname,
            'student_number': i.student_number,
            'department_course': i.course,
            'department_year': i.year,
            'department_section': i.section,
            'student_qrcode': i.qrcode
        } for i in students]

        return jsonify(students_list)

    return redirect(url_for('index'))

@app.route('/manage-records')
def manage_records():
    if 'username' in session:
        option = request.args.get("manage-records-select")
        department_courses = Department.query.with_entities(Department.course).distinct().all()
        department_years = Department.query.with_entities(Department.year).distinct().all()
        department_sections = Department.query.with_entities(Department.section).distinct().all()
        if option=="1":
            departments = Department.query.all()    
            return render_template('manage-department.html', departments=departments,
                                department_courses=department_courses,
                                department_years=department_years,
                                department_sections=department_sections)

        students = Student.query.\
            with_entities(Student.firstname,
                      Student.surname,
                      Student.student_number,
                      Department.course,
                      Department.year,
                      Department.section,
                      Student.qrcode
                      ).\
            join(Department, Student.department == Department.id).all()
        
        return render_template('manage-students.html', 
                               students=students, 
                               department_courses=department_courses,
                               department_years=department_years,
                               department_sections=department_sections)
    return redirect(url_for('index'))

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/scan-qr/<string:year>/<string:section>', methods=['POST', 'GET'])
def scan_qr(year, section):
    if 'username' in session:
        return render_template("qr-scanner.html")
    return redirect(url_for('index'))

@app.route('/student-form/<string:dept>/<string:year>/<string:section>')
def student_form(dept, year, section):
    if 'username' in session:
        current_dept = Department.query.filter_by(course=dept, year=year, section=section).first()
        if not current_dept:
            return redirect(url_for('section_page'))
        return render_template('student-form.html', current_dept=current_dept)
    return redirect(url_for('index'))

@app.route('/section-page', methods=['GET'])
def section_page():
    if 'username' in session:
        selected_dept, selected_year, selected_section = request.args.get('dept'), request.args.get('year'), request.args.get('section')
        student_dept = Department.query.filter_by(course=selected_dept, section=selected_section).first()
        if not student_dept:
            return redirect(url_for('dashboard'))
        students = Student.query.filter_by(department=student_dept.id).all()
        return render_template('students.html', selected_dept=selected_dept, selected_year=selected_year, selected_section=selected_section, students=students)
    return redirect(url_for('index'))

@app.route('/get-section', methods=['POST'])
def get_section():
    if 'username' in session:
        selected_year = request.form.get('year')
        selected_section = request.form.get('section')
        selected_dept = request.form.get('dept')
        return redirect(url_for('section_page', 
                                    dept=selected_dept,
                                    year=selected_year,
                                    section=selected_section))
    return redirect(url_for('index'))

@app.route('/get-section-by-level/<string:year>/<string:dept>')
def get_section_by_level(year, dept):
    if 'username' in session:
        department_section_by_level = Department.query.filter_by(year=year, course=dept).with_entities(Department.section).distinct().all()
        if not department_section_by_level:
            return jsonify({"message": "object empty"}), 401
        data = {
            "section": [j for i in department_section_by_level for j in i]
        }
        return jsonify(data), 201
    return redirect(url_for('index'))

@app.route('/get-year-by-department/<string:dept>')
def get_year_by_department(dept):
    if 'username' in session:
        department_year_by_dept = Department.query.filter_by(course=dept).with_entities(Department.year).distinct().all()
        if not department_year_by_dept:
            return jsonify({"message": "object empty"}), 401
        data = {
            "year": [j for i in department_year_by_dept for j in i]
        }
        return jsonify(data)
    return redirect(url_for('index')), 201

@app.route('/save-department', methods=['POST', 'GET'])
def save_department():
    if 'username' in session:
        course, year, section = request.form['course'].strip(), request.form['year'].strip(), request.form['section'].strip()
        check_dept = Department.query.filter_by(course=course, year=year, section=section).first()
        if check_dept:
            return f"""
                    <script>
                        alert('Cannot add existing department');
                        window.location.href='/dashboard';
                    </script>
                    """
        dept_entry = Department(
            course=course,
            year=year,
            section=section
        )
        db.session.add(dept_entry)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    if 'username' in session:
        department_courses = Department.query.with_entities(Department.course).distinct().all()
        department_years = Department.query.with_entities(Department.year).distinct().all()
        department_sections = Department.query.with_entities(Department.section).distinct().all()
        return render_template('dashboard.html',
                                department_courses=department_courses,
                                department_years=department_years,
                                department_sections=department_sections)
    return redirect(url_for('index'))

@app.route('/admin-login', methods=['POST', 'GET'])
def admin_login():
    username, password = request.form.get('username'), request.form.get('password')
    if request.method == 'POST':
        if Admin.login_true(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        return f""" <script>
                        alert("Wrong Password");
                        window.location.href ="/";
                    </script>
                """
    return redirect(url_for('index'))

@app.route('/add-student', methods=['POST'])
def add_student():
    try:
        firstname = request.form.get('firstname')
        surname = request.form.get('surname')
        student_number = request.form.get('student_number')
        section = request.form.get('section')
        year = request.form.get('year')
        department = request.form.get('department')

        # Generate a QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(student_number)  # You can add any data you want to encode in the QR code.
        qr.make(fit=True)

        # Create the QR code image
        qr_code_image = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code image to a file
        if not os.path.exists(QR_CODE_FOLDER):
            os.makedirs(QR_CODE_FOLDER)

        qr_code_filename = os.path.join(QR_CODE_FOLDER, f'{student_number}.png')
        qr_code_image.save(qr_code_filename)

        # Create a new student record with the QR code data or image path
        student = Student(
            firstname=firstname,
            surname=surname,
            student_number=student_number,
            section=section,
            department=department,
            qrcode=qr_code_filename,
            year=year
            # You can also store the QR code data here if needed
        )

        # Add the student record to the database
        db.session.add(student)
        db.session.commit()
        return f"<script>window.history.go(-2);</script>"
    except:
        return f"<script>alert('Cannot Add Existing Student! Student Number: {student_number}'); history.back();</script>"


@app.route('/process-qr', methods=['POST'])
def process_qr():
    qr_content = request.form.get('qr_content')
    if qr_content:
        student = Student.query.filter_by(student_number=qr_content).first()
        if student:
            student_dept = Department.query.filter_by(id=student.department).first()
            current_date = date.today().strftime("%Y-%m-%d")
            filename = generate_file_name(student_dept.course, student_dept.year, student_dept.section, current_date)
            
            # Check if the CSV file exists
            if not os.path.exists(filename):
                # If it doesn't exist, create the file and write the headers
                with open(filename, mode='w', newline='') as csv_file:
                    csv_writer = csv.DictWriter(csv_file, fieldnames=['student_number', 'firstname', 'surname', 'department'])
                    csv_writer.writeheader()
            
            # Check if the student is already in the CSV file
            student_in_csv = False
            with open(filename, mode='r', newline='') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    if row['student_number'] == student.student_number:
                        student_in_csv = True
                        break

            if not student_in_csv:
                data = [
                    {'student_number': student.student_number,
                     'firstname': student.firstname,
                     'surname': student.surname,
                     'department': student.department
                     }
                ]

                with open(filename, mode='a', newline='') as csv_file:
                    csv_writer = csv.DictWriter(csv_file, fieldnames=data[0].keys())
                    csv_writer.writerows(data)

                thisString = f"""
                                <script>
                                    alert("Student added to CSV file at Course: ({student_dept.course}), Year: ({student_dept.year}) and Section: ({student_dept.section})");
                                    history.back();
                                </script>
                            """
                return thisString
            else:
                
                return f"""
                    <script>
                        alert("Student already in CSV file");
                        history.back()
                    </script>
                    """

        return f"""         
                    <script>
                        alert("No Student Found");
                        history.back()
                    </script>
                    """
    else:
        return f"""
                    <script>
                        alert("Unrecognized QR Code Received");
                        history.back()
                    </script>
                    """

if __name__ == '__main__':
    
    app.run(host="0.0.0.0",port="8000",debug=True)
