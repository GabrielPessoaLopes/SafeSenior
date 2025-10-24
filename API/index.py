from flask import Flask, jsonify, request
from functools import wraps
from datetime import datetime, timezone, timedelta
import os, jwt, requests
import uuid
from dotenv import load_dotenv
import os
import hashlib


load_dotenv()  # loads variables from .env into environment


#The SQL query is automatically built and executed by Supabase based on:
#The GET request made to the Supabase REST endpoint
#The query parameters (params) sent
#The headers (Prefer) like sorting
#Supabase handles authentication, builds the SQL query behind the scenes, 
# executes it on its PostgreSQL database, 
# and returns the filtered and sorted result as JSON.

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "default_secret_key")

# Key
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Common Supabase table URLs
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1"
USER_URL = f"{SUPABASE_REST_URL}/user"
CONNECTION_URL = f"{SUPABASE_REST_URL}/connection"
DEVICE_URL = f"{SUPABASE_REST_URL}/sos_device"
EVENT_URL = f"{SUPABASE_REST_URL}/sos_event"
NOTIF_URL = f"{SUPABASE_REST_URL}/notification"

# HTTP Status Codes
OK = 200
CREATED = 201
BAD_REQUEST = 400
UNAUTHORIZED= 401
FORBIDDEN = 403
NOT_FOUND = 404
CONFLICT= 409
SERVER_ERROR = 500

##################################### Supabase Request Headers ########################################
def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the QuickFix API!"})

#|---------------------------------------------------------------------------------------------------|
#|                                      USER ENDPOINTS                                               |                               |
#|---------------------------------------------------------------------------------------------------|

# ================================== AUTH DECORATOR ================================== 
def auth_user(f):
    """ Decorator to authenticate requests using JWT. 
        Adds request.user_id if valid."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Token is missing"}), UNAUTHORIZED
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            request.user_id = data["id"]
        except:
            return jsonify({"message": "Invalid token"}), UNAUTHORIZED
        return f(*args, **kwargs)
    return decorated

# ================================== REGISTER =====================================
@app.route("/register", methods=["POST"])
def register_user():
    """Register new user"""
    content = request.get_json()
    required = ["user_name", "user_email", "user_password"]
    if not all(k in content for k in required):
        return jsonify({"message": "Missing fields"}), BAD_REQUEST

    email = content["user_email"].lower()

    # Check if email exists
    existing = requests.get(USER_URL, headers=supabase_headers(),
                            params={"user_email": f"eq.{email}"}).json()
    if existing:
        return jsonify({"message": "Email already being used. "}), CONFLICT

    # Hash the password before saving
    encrypted_pass = hashlib.sha256(content["user_password"].encode()).hexdigest()

    new_user = {
        "user_name": content["user_name"],
        "user_email": email,
        "user_password": encrypted_pass
    }

    res = requests.post(USER_URL, headers=supabase_headers(), json=new_user)
    return jsonify({"message": "User created"}), CREATED

# ================================== LOGIN =========================================
@app.route("/login", methods=["POST"])
def login_user():
    """Login with email and password"""
    content = request.get_json()
    if "user_email" not in content or "user_password" not in content:
            return jsonify({"message": "Missing credentials"}), BAD_REQUEST

    res = requests.get(USER_URL, headers=supabase_headers(),
                        params={"user_email": f"eq.{content['user_email'].lower()}"}).json()
    if not res:
        return jsonify({"message": "Invalid credentials"}), UNAUTHORIZED

    user = res[0]
    encrypted_pass = hashlib.sha256(content["user_password"].encode()).hexdigest()
    if encrypted_pass != user["user_password"]:
        return jsonify({"message": "Invalid credentials"}), UNAUTHORIZED

    token = jwt.encode(
        {"id": user["user_id"], "email": user["user_email"],
        "exp":  datetime.now(timezone.utc) + timedelta(hours=8)},
        app.config["SECRET_KEY"], algorithm="HS256"
    )
    return jsonify({"token": token, "userId": user["user_id"]}), OK

# =============================== GET PROFILE ======================================
@app.route("/user/me", methods=["GET"])
@auth_user
def get_profile():
    """Get the authenticated user's profile"""
    res = requests.get(f"{USER_URL}?user_id=eq.{request.user_id}", headers=supabase_headers())
    data = res.json()
    if not data:
        return jsonify({"message": "User not found"}), NOT_FOUND
    return jsonify(data[0]), OK

#|---------------------------------------------------------------------------------------------------|
#|                                      CONNECTION ENDPOINTS                                         |                               |
#|---------------------------------------------------------------------------------------------------|
# ================================== CREATE CONNECTION ==================================
@app.route("/connections", methods=["POST"])
@auth_user
def add_connection():
    """Create connection between carer and cared"""
    content = request.get_json()
    if "cared_id" not in content:
        return jsonify({"message": "Missing cared_id"}), BAD_REQUEST

    if content["cared_id"] == request.user_id:
        return jsonify({"message": "User cannot care for themselves"}), BAD_REQUEST

    payload = {
        "carer_id": request.user_id,
        "cared_id": content["cared_id"]
    }

    res = requests.post(CONNECTION_URL, headers=supabase_headers(), json=payload)
    if res.status_code == CONFLICT:
        return jsonify({"message": "Connection already exists"}), CONFLICT

    return jsonify({"message": "Connection created"}), CREATED


@app.route("/connections", methods=["GET"])
@auth_user
def list_connections():
    """List all cared users for a carer"""
    res = requests.get(f"{CONNECTION_URL}?carer_id=eq.{request.user_id}", headers=supabase_headers())
    return jsonify(res.json()), OK

#|---------------------------------------------------------------------------------------------------|
#|                                        DEVICE ENDPOINTS                                           |                               |
#|---------------------------------------------------------------------------------------------------|
# ================================== REGISTER ==================================
@app.route("/devices", methods=["POST"])
@auth_user
def register_device():
    """Register a new SOS device and returns its ID"""
    device_id = str(uuid.uuid4())
    data = {
        "device_id": device_id,
        "owner_id": request.user_id,
        "is_online": False,
        "last_triggered_at": None
    }

    res = requests.post(DEVICE_URL, headers=supabase_headers(), json=data)
    if res.status_code in (OK, CREATED):
        # Return the new ID
        return jsonify({
            "message": "Device registered",
            "device_id": device_id,
            "owner_id": request.user_id
        }), CREATED
    else:
        return jsonify({"message": "Failed to register device"}), SERVER_ERROR

# ================================== REMOVE ==================================
@app.route("/devices/<uuid:device_id>", methods=["DELETE"])
@auth_user
def remove_device(device_id):
    """Remove a registered device"""
    res = requests.delete(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
    return jsonify({"message": "Device removed"}), OK

# ================================== GET ==================================
@app.route("/devices/<uuid:device_id>", methods=["GET"])
@auth_user
def get_device(device_id):
    """Return single device info"""
    res = requests.get(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
    data = res.json()
    if not data:
        return jsonify({"message": "Device not found"}), NOT_FOUND
    return jsonify(data[0]), OK


# ================================== LIST ==================================
@app.route("/devices", methods=["GET"])
@auth_user
def list_devices():
    """List user devices"""
    res = requests.get(f"{DEVICE_URL}?owner_id=eq.{request.user_id}", headers=supabase_headers())
    return jsonify(res.json()), OK

#|---------------------------------------------------------------------------------------------------|
#|                                      SOS EVENT ENDPOINTS                                          |                               |
#|---------------------------------------------------------------------------------------------------|
# ================================== START SOS EVENT ==================================
@app.route("/sos/start", methods=["POST"])
@auth_user
def start_sos():
    """Start a new SOS alert"""
    content = request.get_json()
    if "device_id" not in content:
        return jsonify({"message": "Missing device_id"}), BAD_REQUEST

    now = datetime.now(timezone.utc).isoformat()
    event = {
        "device_id": content["device_id"],
        "triggered_by": request.user_id,
        "on_at": now
    }

    res = requests.post(EVENT_URL, headers=supabase_headers(), json=event)
    if res.status_code not in (OK, CREATED):
        return jsonify({"message": "Failed to create event"}), SERVER_ERROR

    event_info = res.json()[0]

    # Update device status
    update = {"is_online": True, "last_triggered_at": now}
    requests.patch(f"{DEVICE_URL}?device_id=eq.{content['device_id']}",
                   headers=supabase_headers(), json=update)

    return jsonify({
        "message": "SOS triggered",
        "event_id": event_info["event_id"],
        "device_id": event_info["device_id"]
    }), CREATED

# ================================== STOP SOS EVENT ==================================
@app.route("/sos/stop/<uuid:event_id>", methods=["PATCH"])
@auth_user
def stop_sos(event_id):
    """Mark an SOS alert as ended"""
    data = {"off_at": datetime.utcnow().isoformat(), "handled": True}
    res = requests.patch(f"{EVENT_URL}?event_id=eq.{event_id}", headers=supabase_headers(), json=data)
    return jsonify({"message": "SOS stopped"}), OK

#|---------------------------------------------------------------------------------------------------|
#|                                   NOTIFICATIONS ENDPOINTS                                         |                               |
#|---------------------------------------------------------------------------------------------------|
# ================================== LIST NOTIFICATIONS ==================================
@app.route("/notifications", methods=["GET"])
@auth_user
def get_notifications():
    """List notifications sent to a carer"""
    res = requests.get(f"{NOTIF_URL}?carer_id=eq.{request.user_id}", headers=supabase_headers())
    return jsonify(res.json()), OK

# ================================== SEND NOTIFICATIONS =====================================
@app.route("/notifications/<uuid:event_id>", methods=["POST"])
@auth_user
def send_notifications(event_id):
    """Register notifications for all carers of a cared user"""
    cared_user = request.user_id

    # Find carers linked to this cared user
    carers = requests.get(f"{CONNECTION_URL}?cared_id=eq.{cared_user}", headers=supabase_headers()).json()
    if not carers:
        return jsonify({"message": "No carers connected"}), OK

    for c in carers:
        notif = {"event_id": str(event_id), "carer_id": c["carer_id"]}
        requests.post(NOTIF_URL, headers=supabase_headers(), json=notif)

    return jsonify({"message": f"Notifications sent to {len(carers)} carers"}), OK

# ================================== MAIN ==================================
if __name__ == "__main__":
    app.run(port=8080, debug=True)