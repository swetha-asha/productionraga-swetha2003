from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
from dotenv import load_dotenv

from rag import load_documents, search, keyword_search
from embeddings import generate_embedding
import vector_db

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client safely
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# Session state
session_data = {}

# Load documents at startup
load_documents()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "").strip()
    session_id = data.get("sessionId", "default-session")

    if not message:
        return jsonify({"error": "Message required"}), 400

    # Initialize session
    if session_id not in session_data:
        session_data[session_id] = {
            "state": "IDLE",
            "pending_data": {},
            "current_user": None
        }

    sess = session_data[session_id]

    # ---------------- SIGNUP FLOW ----------------

    if ("sign up" in message.lower() or "signup" in message.lower()) and sess["state"] == "IDLE":
        sess["state"] = "SIGNUP_NAME"
        return jsonify({"reply": "Great! What is your full name?", "retrievedChunks": 0})

    if sess["state"] == "SIGNUP_NAME":
        sess["pending_data"]["name"] = message
        sess["state"] = "SIGNUP_PASS"
        return jsonify({"reply": "Please create a password.", "retrievedChunks": 0})

    if sess["state"] == "SIGNUP_PASS":
        sess["pending_data"]["pass"] = message
        sess["state"] = "SIGNUP_CONFIRM"
        return jsonify({"reply": "Confirm your password.", "retrievedChunks": 0})

    if sess["state"] == "SIGNUP_CONFIRM":
        if message == sess["pending_data"]["pass"]:
            username = sess["pending_data"]["name"]
            vector_db.add_user(username, message)

            sess["state"] = "IDLE"
            sess["current_user"] = username

            return jsonify({
                "reply": f"Account created for {username}. You are now logged in!",
                "retrievedChunks": 0
            })
        else:
            return jsonify({"reply": "Passwords do not match.", "retrievedChunks": 0})

    # ---------------- LOGIN FLOW ----------------

    if "login" in message.lower() and sess["state"] == "IDLE":
        sess["state"] = "LOGIN_NAME"
        return jsonify({"reply": "Enter your username.", "retrievedChunks": 0})

    if sess["state"] == "LOGIN_NAME":
        pwd = vector_db.get_user_password(message)

        if pwd:
            sess["pending_data"]["login_name"] = message
            sess["state"] = "LOGIN_PASS"
            return jsonify({"reply": "Enter your password.", "retrievedChunks": 0})
        else:
            sess["state"] = "IDLE"
            return jsonify({"reply": "User not found.", "retrievedChunks": 0})

    if sess["state"] == "LOGIN_PASS":
        username = sess["pending_data"]["login_name"]
        db_pwd = vector_db.get_user_password(username)

        if db_pwd == message:
            sess["state"] = "IDLE"
            sess["current_user"] = username
            return jsonify({"reply": f"Welcome back {username}!", "retrievedChunks": 0})
        else:
            return jsonify({"reply": "Wrong password.", "retrievedChunks": 0})

    # ---------------- PASSWORD CHANGE ----------------

    if "change password" in message.lower():
        if not sess["current_user"]:
            return jsonify({"reply": "Please login first.", "retrievedChunks": 0})

        sess["state"] = "CHANGE_PASS_NEW"
        return jsonify({"reply": "Enter your new password.", "retrievedChunks": 0})

    if sess["state"] == "CHANGE_PASS_NEW":
        vector_db.update_user_password(sess["current_user"], message)
        sess["state"] = "IDLE"
        return jsonify({"reply": "Password updated successfully.", "retrievedChunks": 0})

    # ---------------- CANCEL ----------------

    if message.lower() == "cancel":
        sess["state"] = "IDLE"
        sess["pending_data"] = {}
        return jsonify({"reply": "Action cancelled.", "retrievedChunks": 0})

    # ---------------- RAG FLOW ----------------

    try:
        greetings = ["hi", "hello", "hey", "who are you"]

        if any(g in message.lower() for g in greetings):
            return jsonify({
                "reply": "Hi! I'm your GenAI Assistant. How can I help?",
                "retrievedChunks": 0
            })

        query_embedding = generate_embedding(message)

        if query_embedding:

            results = search(query_embedding)
            context = "\n".join([r[1] for r in results])

            if client:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Answer using only the context."},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion:{message}"}
                    ],
                    temperature=0.2
                )

                reply = response.choices[0].message.content

            else:
                reply = "API key missing."

        else:

            results = keyword_search(message)

            if results:
                reply = results[0][1]
            else:
                reply = "No relevant info found."

        return jsonify({
            "reply": reply,
            "retrievedChunks": len(results)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------- MAIN ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)