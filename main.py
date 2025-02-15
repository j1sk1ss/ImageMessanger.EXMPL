import os
import time
import tempfile

from contacts import (
    get_contacts,
    remove_contact,
    add_contact
)

from auth import (
    verify_pass,
    generate_access_key,
    verify_access_key
)

from flask_cors import CORS
from flask_socketio import SocketIO
from flask import (
    Flask, 
    jsonify, 
    render_template, 
    request,
    send_from_directory
)

# region Setup

app = Flask(__name__, static_folder='static', template_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024 * 1024
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app=app)


temp_messages: list = []


def require_authorization(f):
    def wrapper(*args, **kwargs):
        auth_key = request.headers.get("Authorization")
        if not verify_access_key(auth_key):
            return jsonify({"error": "Unauthorized"}), 403
        
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# endregion

# region Main

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/auth', methods=['POST'])
def _auth_user():
    data: dict = request.json
    if not data:
        return 400, "No data provided"
    
    password: str | None = data.get("password", None)
    if not password:
        return 400, "Password not provided"
    
    login_data: tuple = verify_pass(password=password)
    if not login_data[0] or not login_data[1]:
        return 404, "User not found"
    
    return {
        "username": login_data[1],
        "key": generate_access_key(username=login_data[1], userpass=login_data[0])
    }

# endregion

# region Contacts

@app.route('/contacts', methods=['GET'])
@require_authorization
def _get_contacts_list():
    username: str = request.headers.get("X-Username")
    return jsonify({"contacts": get_contacts(username=username)})


@app.route('/contacts', methods=['POST'])
@require_authorization
def _add_contact():
    username: str = request.headers.get("X-Username")
    new_contact: str = request.json["contact"]
    if add_contact(username=username, contact=new_contact):
        return "Add success", 200
    else:
        return "Add error", 500


@app.route('/contacts', methods=['DELETE'])
@require_authorization
def _remove_contact():
    username: str = request.headers.get("X-Username")
    contact: str = request.json["contact"]
    if remove_contact(username=username, contact=contact):
        return "Delete success", 200
    else:
        return "Delete error", 500

# endregion

# region Messages

@app.route('/messages', methods=['POST'])
@require_authorization
def _send_message():
    encrypted_message = request.form['message']
    sender = request.form['sender']
    receivers = request.form['receiver'].split(",")
    timestamp = time.time()

    image_url = None
    if 'file' in request.files:
        file = request.files['file']
        if file:
            filename = f"{int(time.time())}_{tempfile.gettempprefix()}"
            filepath = os.path.join('static/uploads/', filename)
            file.save(filepath)

            image_url = filepath

    send_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
    temp_messages.append({
        'from': sender,
        'chat': ",".join(sorted([sender] + receivers)),
        'message': encrypted_message,
        'time': send_time,
        'image': image_url
    })

    return jsonify({"message": "Message sent successfully", "time": send_time})


@app.route('/messages', methods=['GET'])
@require_authorization
def _get_messages():
    source_chat = request.args.get('sender').split(",")
    user_name = request.args.get('receiver')
    if not user_name:
        return jsonify({"error": "Receiver name is required"}), 400

    filtered_messages = []
    for msg in temp_messages:
        if msg['chat'] == ",".join(sorted([user_name] + source_chat)):
            filtered_messages.append(msg)

    return jsonify({ "messages": filtered_messages })


@app.route('/uploads/<filename>')
def _send_image(filename):
    return send_from_directory('static/uploads', filename)


# endregion

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
