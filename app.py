from flask import Flask, render_template, request, redirect, url_for, session,send_file, flash,jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import validators
import datetime
import os
import uuid
import yt_dlp
import subprocess

app = Flask(__name__, template_folder='templates')
app.secret_key = 'Medi@'  # Change this to a strong secret key


# Connect to MongoDB
client = MongoClient("mongodb+srv://kr4785543:1234567890@cluster0.220yz.mongodb.net/")
db = client["mediaguard"]
users_collection = db["users"]
media_collection = db["media"]

# Directory to store uploaded thumbnails
UPLOAD_FOLDER = "./static/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Folder to store downloaded and processed videos
DOWNLOAD_FOLDER = "./static/downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def download_video(url):
    """Downloads the YouTube video and returns the filename."""
    video_id = str(uuid.uuid4())  # Unique ID for each video
    output_template = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.%(ext)s")

    ydl_opts = {
        'format': 'worst',  # Download lowest quality to save bandwidth
        'outtmpl': output_template,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        video_ext = result['ext']
        return f"{video_id}.{video_ext}"
    
def add_text_watermark(input_video, text):
    """Adds a text watermark to the downloaded video, deletes original, and returns the new filename."""
    output_video = input_video.replace(".", "_watermarked.")
    input_path = os.path.join(DOWNLOAD_FOLDER, input_video)
    output_path = os.path.join(DOWNLOAD_FOLDER, output_video)

    command = [
        'ffmpeg',
        '-i', input_path,
        '-vf', f"drawtext=text='{text}':fontcolor=white:fontsize=24:x=10:y=10",
        '-c:a', 'copy',
        output_path
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Delete the original downloaded video
    if os.path.exists(input_path):
        os.remove(input_path)

    return output_video

@app.route('/download')
def download_api():
    """API Endpoint to download and watermark a video."""
    video_url = request.args.get("url")
    watermark_text = "MediaGuard"

    if not video_url:
        return jsonify({"error": "Missing YouTube URL"}), 400

    try:
        downloaded_video = download_video(video_url)
        watermarked_video = add_text_watermark(downloaded_video, watermark_text)
        
        return jsonify({
            "message": "Video processed successfully",
            "download_url": f"/download/{watermarked_video}"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        if email=="admin@mediaguard.com" and password=="1234567890":
            session['role'] = "admin"
            return redirect("/admindashboard")

        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["email"] = user["email"]
            session["role"] = "user"
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "danger")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            flash("Email already registered!", "warning")
            return redirect(url_for("register"))
        existing_user = users_collection.find_one({"mobile": mobile})
        if existing_user:
            flash("Email already registered!", "warning")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        user_data = {"name": name, "email": email, "mobile": mobile, "password": hashed_password}
        users_collection.insert_one(user_data)

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/admin/add-video", methods=["GET", "POST"])
def add_video():
    if request.method == "POST":
        try:
            # Ensure only admins can add videos
            if "role" not in session or session["role"] != "admin":
                flash("Unauthorized access", "danger")
                return redirect(url_for("login"))

            # Get form data
            title = request.form.get("title")
            description = request.form.get("description", "").strip()
            category = request.form.get("category", "").strip()
            release_date = request.form.get("release_date", "").strip()
            video_url = request.form.get("video_url", "").strip()
            duration = request.form.get("duration", "0").strip()
            language = request.form.get("language", "").strip()
            age_rating = request.form.get("age_rating", "").strip()
            
            if not title or not category or not video_url or not release_date:
                flash("Title, Category, Release Date, and Video URL are required fields.", "error")
                return redirect(url_for("add_video"))

            # Convert release_date to datetime format
            try:
                release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.", "error")
                return redirect(url_for("add_video"))

            # Validate thumbnail file
            if "thumbnail" not in request.files:
                flash("No thumbnail file provided", "error")
                return redirect(url_for("add_video"))

            thumbnail = request.files["thumbnail"]
            if thumbnail and allowed_file(thumbnail.filename):
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{secure_filename(title)}_{timestamp}.{thumbnail.filename.rsplit('.', 1)[1].lower()}"
                thumbnail_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

                # Save the file securely
                thumbnail.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            else:
                flash("Invalid thumbnail file type", "error")
                return redirect(url_for("add_video"))

            # Save video details to MongoDB
            video_data = {
                "title": title,
                "description": description,
                "category": category,
                "release_date": release_date,
                "video_url": video_url,
                "duration": int(duration),
                "language": language,
                "age_rating": age_rating,
                "thumbnail": thumbnail_path  # Storing relative path
            }

            video_id = media_collection.insert_one(video_data).inserted_id
            flash(f"Video added successfully! ID: {video_id}", "success")
            return redirect(url_for("add_video"))

        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for("add_video"))

    return render_template("add-video.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        videos = list(media_collection.find())
        return render_template("dashboard.html",videos=videos)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/add-media")
def addmedia():
    return render_template("add-video.html")

@app.route("/admindashboard", methods=["GET"])
def get_all_videos():
    try:
        videos = list(media_collection.find())
        return render_template("admindashboard.html",videos=videos)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/view", methods=["GET"])
def view_video():
    video_id = request.args.get("id")  # Get video ID from query parameters
    if not video_id:
        return "Video ID is required", 400

    # Fetch video details from MongoDB
    video = media_collection.find_one({"_id": ObjectId(video_id)})

    if not video:
        return "Video not found", 404

    # Convert MongoDB ObjectId and Date to string format
    video["_id"] = str(video["_id"])

    return render_template("view.html", video=video)  # Render HTML page

@app.route("/edit")
def vid_edit():
    id=request.args.get("id")
    session['id']=id
    video=media_collection.find_one({"_id":ObjectId(id)})
    return render_template("edit.html",video=video)

@app.route("/edit", methods=["POST"])
def edit_video():
    id = session.get('id')
    if not id:
        return jsonify({"error": "Session expired or ID missing"}), 400

    # Convert release_date safely
    try:
        release_date = datetime.datetime.strptime(request.form.get("release_date"), "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    try:
        duration = int(request.form.get("duration"))
    except ValueError:
        return jsonify({"error": "Duration must be a number"}), 400

    # Handle Thumbnail Upload
    thumbnail = request.files.get("thumbnail")
    existing_thumbnail = request.form.get("existing_thumbnail")  # Get the old thumbnail path

    if thumbnail and allowed_file(thumbnail.filename):
        # Generate a secure filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{secure_filename(request.form.get('title'))}_{timestamp}.{thumbnail.filename.rsplit('.', 1)[1].lower()}"
        thumbnail_path = os.path.join(UPLOAD_FOLDER, filename)

        # Save the new thumbnail
        thumbnail.save(thumbnail_path)
    else:
        thumbnail_path = existing_thumbnail  # Keep the old thumbnail if no new one is uploaded

    # Update video details
    updated_data = {
        "title": request.form.get("title"),
        "description": request.form.get("description"),
        "category": request.form.get("category"),
        "release_date": release_date,
        "language": request.form.get("language"),
        "age_rating": request.form.get("age_rating"),
        "duration": duration,
        "thumbnail": thumbnail_path,  # Updated thumbnail path
        "video_url": request.form.get("video_url"),
    }

    result = media_collection.update_one({"_id": ObjectId(id)}, {"$set": updated_data})

    if result.modified_count > 0:
        flash("Video updated successfully!", "success")
        return redirect("/admindashboard")
    else:
        flash("No changes were made.", "warning")
        return redirect("/edit")   
### 📌 4. Delete Video
@app.route("/delete", methods=["POST"])
def delete_video():
    video_id = request.form.get("id")
    result = media_collection.delete_one({"_id": ObjectId(video_id)})

    if result.deleted_count > 0:
        return redirect("/admindashboard")
    else:
        return jsonify({"error": "Video not found"}), 404
    
@app.route("/watch")
def watch():
    url=request.args.get("url")
    return render_template("watch.html",video=url)

if __name__ == '__main__':
    app.run(debug=True)
