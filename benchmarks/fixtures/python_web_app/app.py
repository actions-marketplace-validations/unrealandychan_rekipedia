from flask import Flask, jsonify

app = Flask(__name__)

class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

def get_user(user_id: int) -> User:
    """Retrieve a user by ID."""
    return User("Alice", "alice@example.com")

def create_user(name: str, email: str) -> User:
    """Create a new user."""
    return User(name, email)

@app.route("/users/<int:user_id>")
def index(user_id: int):
    user = get_user(user_id)
    return jsonify({"name": user.name})
