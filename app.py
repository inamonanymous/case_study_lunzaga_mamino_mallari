from flask import Flask, request, render_template, redirect, url_for, session
from flask_migrate import Migrate
import qrcode
import os
from model.models import db, Student, Admin
import csv
from datetime import date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///sqlite.db"
db.init_app(app)
QR_CODE_FOLDER = 'static/qrcodes'  # Folder to save QR code images
app.secret_key = "mamino_mallari_lunzaga"
migrate = Migrate(app, db)

def generate_file_name(year_folder, section_folder, current_date=date.today().strftime("%Y-%m-%d")):
    data_folder = os.path.join('attendance_data', year_folder, section_folder)
    os.makedirs(data_folder, exist_ok=True)

    return os.path.join(data_folder, f"attendance_at_{current_date}.csv")

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/scan-qr/<string:year>/<string:section>', methods=['POST', 'GET'])
def scan_qr(year, section):
    if 'username' in session:
        return render_template("qr-scanner.html")
    return redirect(url_for('index'))

@app.route('/student-form')
def student_form():
    if 'username' in session:
        return render_template('student-form.html')
    return redirect(url_for('index'))

@app.route('/section-page', methods=['GET'])
def section_page():
    if 'username' in session:
        selected_year, selected_section = request.args.get('year'), request.args.get('section')
        students = Student.query.filter_by(section=selected_section).all()
        return render_template('students.html', selected_year=selected_year, selected_section=selected_section, students=students)
    return redirect(url_for('index'))

@app.route('/get-section', methods=['POST'])
def get_section():
    if 'username' in session:
        selected_year = request.form.get('year')
        selected_section = request.form.get('section')
        return redirect(url_for('section_page', year=selected_year, section=selected_section))
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['POST', 'GET'])
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html')
    return redirect(url_for('index'))

@app.route('/admin-login', methods=['POST', 'GET'])
def admin_login():
    username, password = request.form.get('username'), request.form.get('password')
    if request.method == 'POST':
        if Admin.login_true(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        return f"wrong password"
    print(Admin.login_true(username, password))
    print('here')
    return redirect(url_for('index'))

@app.route('/add-student', methods=['POST'])
def add_student():
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

    return redirect(url_for('dashboard'))

@app.route('/process-qr', methods=['POST'])
def process_qr():
    qr_content = request.form.get('qr_content')
    if qr_content:
        student = Student.query.filter_by(student_number=qr_content).first()
        if student:
            year = student.year
            section = student.section
            current_date = date.today().strftime("%Y-%m-%d")
            filename = generate_file_name(year, section, current_date)
            
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
                return f"Student added to CSV file at {year}, Year and {section}, Section"
            else:
                return "Student already in CSV file."

        return f"{student.firstname}"
    else:
        return 'No QR code content received'

if __name__ == '__main__':
    
    app.run(host="0.0.0.0",port="5000",debug=True)
