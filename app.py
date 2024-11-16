from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from werkzeug.utils import secure_filename
from flask import render_template


# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder to save uploaded files
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov', 'webm', 'html'}  # Allowed file types

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Database Models
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    slides = db.relationship('Slide', backref='course', lazy=True)

class Slide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(500), nullable=True)  # URL for images, videos, iframes
    media_type = db.Column(db.String(50), nullable=False)  # 'text', 'image', 'video', 'iframe'
    transcript = db.Column(db.Text, nullable=True)
    local_file_path = db.Column(db.String(500), nullable=True)  # Path for local file storage
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# Routes

@app.route('/')
def home():
    # Fetch all courses from the database
    courses = Course.query.all()

    # Render the Jinja template and pass the courses data to the template
    return render_template('courses.html', courses=courses)


@app.route('/mycourse/<int:course_id>')
def mycourse(course_id):
    # Fetch the course from the database by ID
    course = Course.query.get(course_id)

    if not course:
        return jsonify({"error": "Course not found."}), 404

    # Fetch the slides associated with the course
    slides = [{"id": slide.id, "content": slide.content, "media_url": slide.media_url, "media_type": slide.media_type} for slide in course.slides]

    # Render the Jinja template and pass the course and slides data to the template
    return render_template('mycourse.html', course=course, slides=slides)








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

    data = request.form
    content = data.get('content')  # For text content
    media_type = data.get('media_type')  # 'text', 'image', 'video', 'iframe'
    transcript = data.get('transcript')

    # Handle local file upload and URL-based media
    media_url = None
    local_file_path = None

    if 'file' in request.files:  # Check for file upload
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            local_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_file_path)
            media_type = 'image' if filename.lower().endswith(('jpg', 'jpeg', 'png', 'gif')) else 'video'
        else:
            return jsonify({"error": "Invalid file type or no file provided."}), 400
    elif 'media_url' in data:  # Check for media URL
        media_url = data.get('media_url')
        if not media_url:
            return jsonify({"error": "Media URL is required."}), 400

    # Validate media type
    if media_type not in ['text', 'image', 'video', 'iframe']:
        return jsonify({"error": "Invalid media type."}), 400

    # Create slide with optional transcript, media URL, or local file path
    slide = Slide(
        content=content if media_type == 'text' else None,
        media_url=media_url if media_type != 'text' else None,
        local_file_path=local_file_path if media_type != 'text' else None,
        media_type=media_type,
        transcript=transcript,
        course_id=course_id
    )
    db.session.add(slide)
    db.session.commit()

    return jsonify({
        "message": "Slide created successfully!",
        "slide_id": slide.id,
        "media_type": slide.media_type,
        "transcript": transcript if transcript else "No transcript provided.",
        "media_url": media_url if media_url else local_file_path
    })

@app.route('/delete_slide/<int:slide_id>', methods=['DELETE'])
def delete_slide(slide_id):
    # Fetch the slide from the database by ID
    slide = Slide.query.get(slide_id)

    if not slide:
        return jsonify({"error": "Slide not found."}), 404

    # Delete the slide
    db.session.delete(slide)
    db.session.commit()

    return jsonify({"message": "Slide deleted successfully!"}), 200



# Route to edit a slide
@app.route('/edit_slide/<int:slide_id>', methods=['PUT'])
def edit_slide(slide_id):
    slide = Slide.query.get(slide_id)

    if not slide:
        return jsonify({"error": "Slide not found."}), 404

    data = request.json
    content = data.get('content', slide.content)
    transcript = data.get('transcript', slide.transcript)

    # Handle file upload (if any)
    if 'file' in request.files:
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Save the file
            file.save(file_path)

            # Update media URL with the file path
            slide.media_url = file_path

    # Update slide's content and transcript
    slide.content = content
    slide.transcript = transcript

    # Commit changes to database
    db.session.commit()

    return jsonify({
        "message": "Slide updated successfully!",
        "slide_id": slide.id,
        "content": slide.content,
        "transcript": slide.transcript,
        "media_url": slide.media_url
    }), 200




@app.route('/get_course/<int:course_id>', methods=['GET'])
def get_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found."}), 404

    slides = [{"id": slide.id, "content": slide.content, "media_url": slide.media_url, "local_file_path": slide.local_file_path, "media_type": slide.media_type, "transcript": slide.transcript} for slide in course.slides]
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

    slides = []
    for slide in course.slides:
        if slide.media_type == 'text':
            slides.append({"id": slide.id, "content": slide.content, "transcript": slide.transcript if slide.transcript else "No transcript"})
        elif slide.media_type == 'image' or slide.media_type == 'video':
            media_path = slide.local_file_path if slide.local_file_path else slide.media_url
            slides.append({"id": slide.id, "media_url": media_path, "media_type": slide.media_type, "transcript": slide.transcript if slide.transcript else "No transcript"})
        elif slide.media_type == 'iframe':
            slides.append({"id": slide.id, "media_url": slide.media_url, "media_type": slide.media_type, "transcript": slide.transcript if slide.transcript else "No transcript"})

    preview_data = {
        "course_title": course.title,
        "course_description": course.description,
        "total_slides": len(slides),
        "slides_preview": slides
    }

    return jsonify(preview_data)

# Main execution
if __name__ == '__main__':
    # Make sure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)
