from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
from dotenv import load_dotenv

from rag import load_documents, search
from embeddings import generate_embedding
import vector_db

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# session state for the demo (remains temporary for flow tracking)
session_data = {} # session_id: {state: str, pending_data: dict, current_user: str}

# Trigger document loading and embedding generation on startup
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

    # Initialize session if not exists
    if session_id not in session_data:
        session_data[session_id] = {"state": "IDLE", "pending_data": {}, "current_user": None}
    
    sess = session_data[session_id]

    # --- STATE MACHINE LOGIC ---
    
    # SIGNUP FLOW
    if ("sign up" in message.lower() or "signup" in message.lower()) and sess["state"] == "IDLE":
        sess["state"] = "SIGNUP_NAME"
        return jsonify({"reply": "Great! Let's get you registered. What is your full name?", "retrievedChunks": 0})

    if sess["state"] == "SIGNUP_NAME":
        sess["pending_data"]["name"] = message
        sess["state"] = "SIGNUP_PASS"
        return jsonify({"reply": f"Nice to meet you, {message}! Please set a new password for your account.", "retrievedChunks": 0})

    if sess["state"] == "SIGNUP_PASS":
        sess["pending_data"]["pass"] = message
        sess["state"] = "SIGNUP_CONFIRM"
        return jsonify({"reply": "Please confirm your password (type it again).", "retrievedChunks": 0})

    if sess["state"] == "SIGNUP_CONFIRM":
        if message == sess["pending_data"]["pass"]:
            username = sess["pending_data"]["name"]
            vector_db.add_user(username, message) # Persistent Save
            sess["state"] = "IDLE"
            sess["current_user"] = username
            return jsonify({
                "reply": f"Success! Account created for {username}. You are now logged in! ✅\nNow you can explore your documents.", 
                "retrievedChunks": 0,
                "action": "AUTH_SUCCESS" 
            })
        else:
            return jsonify({"reply": "Passwords do not match! Please try again or type 'cancel'.", "retrievedChunks": 0})

    # LOGIN FLOW
    if "login" in message.lower() and sess["state"] == "IDLE":
        sess["state"] = "LOGIN_NAME"
        return jsonify({"reply": "Sure thing. What is your username/name?", "retrievedChunks": 0})

    if sess["state"] == "LOGIN_NAME":
        pwd = vector_db.get_user_password(message) # Persistent Check
        if pwd:
            sess["pending_data"]["login_name"] = message
            sess["state"] = "LOGIN_PASS"
            return jsonify({"reply": f"Found you, {message}! What is your password?", "retrievedChunks": 0})
        else:
            sess["state"] = "IDLE"
            return jsonify({"reply": "I couldn't find an account with that name. Would you like to 'sign up' instead?", "retrievedChunks": 0})

    if sess["state"] == "LOGIN_PASS":
        username = sess["pending_data"]["login_name"]
        db_pwd = vector_db.get_user_password(username)
        if db_pwd == message:
            sess["state"] = "IDLE"
            sess["current_user"] = username
            return jsonify({"reply": f"Welcome back, {username}! You are now logged in.", "retrievedChunks": 0})
        else:
            return jsonify({"reply": "Incorrect password. Please try again or type 'cancel'.", "retrievedChunks": 0})

    # CHANGE PASSWORD FLOW
    if "change password" in message.lower() and sess["state"] == "IDLE":
        if not sess["current_user"]:
            return jsonify({"reply": "You need to be logged in to change your password. Try 'login' first.", "retrievedChunks": 0})
        sess["state"] = "CHANGE_PASS_NEW"
        return jsonify({"reply": f"Ok {sess['current_user']}, please enter your NEW password.", "retrievedChunks": 0})

    if sess["state"] == "CHANGE_PASS_NEW":
        vector_db.update_user_password(sess["current_user"], message) # Persistent Update
        sess["state"] = "IDLE"
        return jsonify({"reply": "Your password has been successfully updated! 🔒", "retrievedChunks": 0})

    # CANCEL FLOW
    if message.lower() == "cancel":
        sess["state"] = "IDLE"
        sess["pending_data"] = {}
        return jsonify({"reply": "Action cancelled. How else can I help you?", "retrievedChunks": 0})

    # --- REGULAR RAG / FALLBACK LOGIC ---
    try:
        # 0. Basic Greeting Check
        greetings = ["hi", "hello", "hey", "hola", "greetings", "who are you"]
        if any(word in message.lower() for word in greetings):
            return jsonify({
                "reply": "Hi! I'm your GenAI Assistant. I can help you with account settings like resetting passwords or security. What can I do for you?",
                "retrievedChunks": 0
            })

        # 1. Try to generate query embedding
        query_embedding = generate_embedding(message)
        
        if query_embedding:
            # RAG flow with OpenAI
            results = search(query_embedding)
            context = "\n".join([r[1] for r in results])
            
            try:
                # Try to generate response using OpenAI
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful GenAI Assistant. Answer the user's question ONLY using the provided context. If the answer isn't in the context, say you don't know based on the provided docs."},
                        {"role": "user", "content": f"Context:\n{context}\n\nUser Question:\n{message}"}
                    ],
                    temperature=0.2,
                    max_tokens=512
                )
                reply = response.choices[0].message.content
            except Exception as api_err:
                print(f"Chat API failed: {api_err}. Falling back to direct context.")
                # If Chat API fails (quota), return the best retrieved document directly
                reply = f"[Offline Mode] Based on your docs: {results[0][1]}" if results else "I found the relevant documents, but I'm having trouble phrasing a response right now."
        else:
            # Fallback for Embedding API failure (quota exceeded)
            from rag import keyword_search
            print("Embedding failed, falling back to keyword search.")
            results = keyword_search(message)
            if results:
                reply = f"[Offline Search] I found this relevant information: {results[0][1]}"
            else:
                reply = "I can't find specific info on that. You can ask me about password resets, account creation, or security settings!"

        return jsonify({
            "reply": reply,
            "retrievedChunks": len(results)
        })
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
