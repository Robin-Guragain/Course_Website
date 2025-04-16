
from flask import Flask, render_template, request, redirect, url_for, flash, session
from sqlalchemy import create_engine, Column, Integer, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from flask_bcrypt import Bcrypt
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key-here'
bcrypt = Bcrypt(app)

Base = declarative_base()
class Users(Base):
    __tablename__ = "Users"

    user_id = Column(Integer, primary_key=True)
    username = Column(Text)
    password = Column(Text)
    user_type = Column(Text)

class Teachers(Base):
    __tablename__ = "Teachers"

    teacher_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"))
    name = Column(Text)

class Students(Base):
    __tablename__ = "Students"

    student_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("Users.user_id"))
    name = Column(Text)  # Must have a name


class Evaluations(Base):
    __tablename__ = "Evaluations"

    evaluation_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("Students.student_id"))
    teacher_id = Column(Integer, ForeignKey("Teachers.teacher_id"))
    total_marks = Column(Float)
    student_marks = Column(Float)
    name = Column(Text)

class Feedback(Base):
    __tablename__ = "Feedback"

    feedback_id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("Teachers.teacher_id"))
    feedback_Q1 = Column(Text)
    feedback_Q2 = Column(Text)
    feedback_Q3 = Column(Text)
    feedback_Q4 = Column(Text)


class RemarkRequest(Base):
    __tablename__ = "remark_requests"

    request_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("Students.student_id"))
    teacher_id = Column(Integer, ForeignKey("Teachers.teacher_id"))
    evaluation_id = Column(Integer, ForeignKey("Evaluations.evaluation_id"))
    reason = Column(Text)
    status = Column(Text)


engine = create_engine("sqlite:///course_portal.db", echo=True)
Session = sessionmaker(bind=engine)
database = Session()

Base.metadata.create_all(engine)

def generate_unique_id(table, id, min_value=00000, max_value=99999):
    for i in range(500):
        random_id = random.randint(min_value, max_value)
        exists = database.query(table).filter(getattr(table, id) == random_id).first()
        if not exists:
            return random_id


def create_test_users():

    existing_users = database.query(Users).count()
    if existing_users > 0:
        return

    test_users = [
        {"username": "student1", "password": "student1", "user_type": "student"},
        {"username": "student2", "password": "student2", "user_type": "student"},
        {"username": "instructor1", "password": "instructor1", "user_type": "teacher"},
        {"username": "instructor2", "password": "instructor2", "user_type": "teacher"}
    ]

    for user_data in test_users:
        hashed_password = bcrypt.generate_password_hash(user_data["password"]).decode('utf-8')
        new_user = Users(
            user_id=generate_unique_id(Users, 'user_id'),
            username=user_data["username"],
            password=hashed_password,
            user_type=user_data["user_type"]
        )
        database.add(new_user)
        database.commit()

    student1 = database.query(Users).filter_by(username="student1").first()

create_test_users()


@app.route('/successful_login_teacher', methods=['GET', 'POST'])
def successful_login_teacher():
    return render_template('teacher_home.html')

@app.route('/successful_login_student', methods=['GET', 'POST'])
def successful_login_student():
    return render_template('student_home.html')

@app.route('/submit_feedback_students', methods=['GET', 'POST'])
def submit_feedback_students():
    if request.method == 'POST':
        feedback_id = generate_unique_id(Feedback,'feedback_id')
        teacher_id = request.form.get('teacher_id')
        feedback_Q1 = request.form.get('feedback_Q1')
        feedback_Q2 = request.form.get('feedback_Q2')
        feedback_Q3 = request.form.get('feedback_Q3')
        feedback_Q4 = request.form.get('feedback_Q4')
        teacher_id = int(teacher_id)

        new_feedback = Feedback(feedback_id=feedback_id, teacher_id=teacher_id, feedback_Q1=feedback_Q1, feedback_Q2=feedback_Q2, feedback_Q3=feedback_Q3, feedback_Q4=feedback_Q4)
        database.add(new_feedback)
        database.commit()
        flash("Your feedback has been submitted successfully!", "success")
        return redirect(url_for('submit_feedback_students'))

    else:
        teachers = database.query(Teachers).all()
        return render_template('submit_feedback_students.html', teachers=teachers)

@app.route('/view_marks_students', methods=['GET', 'POST'])
def view_marks_students():
    if request.method == 'POST':
        request_id = generate_unique_id(RemarkRequest,'request_id')
        reason = request.form.get('request')
        status = "pending"
        student_id = request.form.get('student_id')
        teacher_id = request.form.get('teacher_id')
        evaluation_id = request.form.get('evaluation_id')

        new_request = RemarkRequest(request_id=request_id, reason=reason, status=status, student_id=student_id, teacher_id=teacher_id, evaluation_id=evaluation_id)
        database.add(new_request)
        database.commit()
        flash("Remark request submitted successfully", "success")
        return redirect(url_for('view_marks_students'))

    else:
        student = database.query(Students).filter_by(user_id=session['user_id']).first()
        evaluations = (
            database.query(Evaluations, Teachers)
            .join(Teachers, Teachers.teacher_id == Evaluations.teacher_id)
            .filter(Evaluations.student_id == student.student_id)
            .order_by(Evaluations.name)
            .all()
        )

        requests = (
            database.query(RemarkRequest, Evaluations, Teachers)
            .join(Evaluations, Evaluations.evaluation_id == RemarkRequest.evaluation_id)
            .join(Teachers, Teachers.teacher_id == RemarkRequest.teacher_id)
            .filter(RemarkRequest.student_id == student.student_id)
            .all()
        )

        return render_template('view_marks_students.html', evaluations=evaluations, requests=requests)


@app.route('/view_student_marks', methods=['GET', 'POST'])
def view_student_marks():
    if request.method == 'POST':
        evaluation_id = generate_unique_id(Evaluations,'evaluation_id')
        student_id = request.form.get('student_id')
        teacher = database.query(Teachers).filter_by(user_id=session['user_id']).first()
        total_marks = request.form.get('total_marks')
        student_marks = request.form.get('student_marks')
        name = request.form.get('evaluation_name')
        student_id = int(student_id)

        evaluation = Evaluations(evaluation_id=evaluation_id, student_id=student_id, teacher_id=teacher.teacher_id, total_marks=total_marks, student_marks=student_marks, name=name)
        database.add(evaluation)
        database.commit()
        flash("Remark request submitted successfully", "success")
        return redirect(url_for('view_student_marks'))

    else:

        evaluations = (
            database.query(Evaluations, Students)
            .join(Students, Students.student_id == Evaluations.student_id)
            .order_by(Students.name)
            .all()
        )
        students = database.query(Students).all()

        return render_template('view_students_grades.html',evaluations=evaluations,students=students)

    return render_template('view_students_grades.html')

@app.route('/view_feedback', methods=['GET', 'POST'])
def view_feedback():
    teacher = database.query(Teachers).filter_by(user_id=session['user_id']).first()
    feedback = database.query(Feedback).filter_by(teacher_id=teacher.teacher_id).all()
    return render_template('view_feedback_instructor.html',feedback_items = feedback)

@app.route('/view_remark_requests', methods=['GET', 'POST'])
def view_remark_requests():
    if request.method == 'POST':
        request_id = request.form.get('request_id')
        status = request.form.get('action')
        remark_request = database.query(RemarkRequest).filter_by(request_id=request_id).first()
        if remark_request:
            if status == 'approve':
                remark_request.status = 'approved'
            elif status == 'reject':
                remark_request.status = 'rejected'
            database.commit()
        return redirect(url_for('view_remark_requests'))

    else:
        teacher = database.query(Teachers).filter_by(user_id=session['user_id']).first()
        requests = database.query(
            RemarkRequest,
            Students.name.label('student_name'),
            Evaluations.name.label('evaluation_name')
        ).join(
            Evaluations, Evaluations.evaluation_id == RemarkRequest.evaluation_id
        ).join(
            Students, Students.student_id == RemarkRequest.student_id
        ).filter(
            RemarkRequest.teacher_id == teacher.teacher_id
        ).all()


    return render_template('remark_requests_view.html', requests=requests)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if 'username' in request.form:
            username = request.form.get("username")
            password = request.form.get("password")
            user = database.query(Users).filter_by(username=username).first()

            if user and bcrypt.check_password_hash(user.password, password):
                session.clear()
                session.update({
                    'user_id': user.user_id,
                    'username': user.username,
                    'user_type': user.user_type.lower(),
                    'permanent': True
                })
                session.modified = True
                if user.user_type.lower() in ["teacher", "instructor"]:  # Handle both
                    return redirect(url_for('successful_login_teacher'))
                elif user.user_type.lower() == "student":
                    return redirect(url_for('successful_login_student'))

            else:
                flash("Invalid username or password", "danger")
                return redirect(url_for('login_page'))

        elif 'new_username' in request.form:
            username = request.form['new_username']
            password = request.form['new_password']
            user_type = request.form['user_type'].lower()
            name = request.form['name']

            check_user = database.query(Users).filter_by(username=username).first()

            if check_user:
                flash("Username already exists!", "danger")
                return redirect(url_for('login_page'))

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user_id = generate_unique_id(Users, 'user_id')
            new_user = Users(user_id=user_id,username=username, password=hashed_password,user_type=user_type)

            if (user_type == 'teacher'):
                new_teacher = Teachers(teacher_id=generate_unique_id(Teachers, 'teacher_id'), user_id=user_id, name=name)
                database.add(new_teacher)
            elif (user_type == 'student'):
                new_student = Students(student_id=generate_unique_id(Students, 'student_id'), user_id=user_id, name=name)
                database.add(new_student)

            database.add(new_user)
            database.commit()


            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login_page'))

    return render_template('Course website.html')




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
