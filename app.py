from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import bcrypt
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI) 
app = Flask(__name__)
CORS(app)


db = client["taskDB"]
tasks_collection = db["tasks"]
users_collection = db["users"]

# =========================
#  Home
# =========================
@app.route("/")
def home():
    return "API Running 🚀"

# =========================
# SIGNUP
# =========================
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "All fields required"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 400

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed
    })

    return jsonify({"message": "Signup successful"})

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"error": "Invalid password"}), 401

    return jsonify({
        "message": "Login success",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        }
    })

# =========================
# PRIORITY LOGIC
# =========================
def get_priority(title):
    title = title.lower()

    if "urgent" in title or "asap" in title:
        return "High"
    elif "later" in title or "optional" in title:
        return "Low"
    else:
        return "Medium"

# =========================
#  ADD TASK
# =========================
@app.route("/add-task", methods=["POST"])
def add_task():
    data = request.json
    title = data.get("title")

    if not title:
        return jsonify({"error": "Title required"}), 400

    priority = get_priority(title)

    task = {
        "title": title,
        "status": "pending",
        "priority": priority,
        "created_at": datetime.now().isoformat()
    }

    tasks_collection.insert_one(task)

    return jsonify({
        "message": "Task added",
        "priority": priority
    })

# =========================
#  GET TASKS
# =========================
@app.route("/tasks")
def get_tasks():
    tasks = []

    for t in tasks_collection.find().sort("_id", -1):
        t["_id"] = str(t["_id"])
        tasks.append(t)

    return jsonify(tasks)

# =========================
# TOGGLE TASK
# =========================
@app.route("/toggle/<id>", methods=["PUT"])
def toggle_task(id):
    from bson.objectid import ObjectId

    task = tasks_collection.find_one({"_id": ObjectId(id)})

    if not task:
        return jsonify({"error": "Task not found"}), 404

    new_status = "completed" if task["status"] == "pending" else "pending"

    tasks_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": new_status}}
    )

    return jsonify({"message": "Updated"})

# =========================
# DELETE TASK
# =========================
@app.route("/delete/<id>", methods=["DELETE"])
def delete_task(id):
    from bson.objectid import ObjectId

    tasks_collection.delete_one({"_id": ObjectId(id)})

    return jsonify({"message": "Deleted"})

# =========================
#  ANALYTICS
# =========================
@app.route("/analytics")
def analytics():
    tasks = list(tasks_collection.find())

    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "completed")

    rate = (completed / total * 100) if total > 0 else 0

    return jsonify({
        "total": total,
        "completed": completed,
        "rate": round(rate, 2)
    })

# =========================
#  RUN SERVER
# =========================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)