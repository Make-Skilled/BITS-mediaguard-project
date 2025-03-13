from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates')
app.secret_key = 'Medi@'  # Change this to a strong secret key

# Connect to MongoDB
client = MongoClient("mongodb+srv://kr4785543:1234567890@cluster0.220yz.mongodb.net/")
db = client["mediaguard"]
users_collection = db["users"]

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        if email=="admin@mediaguard.com" and password=="1234567890":
            return render_template("admindashboard.html")

        user = users_collection.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["email"] = user["email"]
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

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/dashoard")
def dashboard():
    return render_template("dashboard.html")

if __name__ == '__main__':
    app.run(debug=True)
