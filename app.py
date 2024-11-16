from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Models
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    slides = db.relationship('Slide', backref='course', lazy=True)

class Slide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    transcript = db.Column(db.Text, nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# Routes
@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Course Creator API!"})

@app.route('/create_course', methods=['POST'])
def create_course():
    data = request.json
    title = data.get('title')
    description = data.get('description')

    if not title or not description:
        return jsonify({"error": "Title and description are required."}), 400

    course = Course(title=title, description=description)
    db.session.add(course)
    db.session.commit()
    return jsonify({"message": "Course created successfully!", "course_id": course.id})

@app.route('/create_slide/<int:course_id>', methods=['POST'])
def create_slide(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found."}), 404

    data = request.json
    content = data.get('content')
    transcript = data.get('transcript')

    if not content:
        return jsonify({"error": "Slide content is required."}), 400

    # Create slide with optional transcript
    slide = Slide(content=content, transcript=transcript, course_id=course_id)
    db.session.add(slide)
    db.session.commit()

    return jsonify({
        "message": "Slide created successfully!",
        "slide_id": slide.id,
        "transcript": transcript if transcript else "No transcript provided."
    })

@app.route('/get_course/<int:course_id>', methods=['GET'])
def get_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found."}), 404

    slides = [{"id": slide.id, "content": slide.content, "transcript": slide.transcript} for slide in course.slides]
    return jsonify({
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "slides": slides
    })

@app.route('/preview_slides/<int:course_id>', methods=['GET'])
def preview_slides(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found."}), 404

    slides = [{"id": slide.id, "content": slide.content, "transcript": slide.transcript if slide.transcript else "No transcript available."} for slide in course.slides]
    
    # Improved presentation of slides preview
    preview_data = {
        "course_title": course.title,
        "course_description": course.description,
        "total_slides": len(slides),
        "slides_preview": slides
    }

    return jsonify(preview_data)

# Main execution
if __name__ == '__main__':
    app.run(debug=True)
