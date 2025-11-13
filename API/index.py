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
#|                                      USER ENDPOINTS                                               |                               
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
    """Create a symmetric connection between two users"""
    content = request.get_json()
    if "other_user_id" not in content:
        return jsonify({"message": "Missing other_user_id"}), BAD_REQUEST

    if content["other_user_id"] == request.user_id:
        return jsonify({"message": "User cannot connect to themselves"}), BAD_REQUEST

    payload = {
        "user1_id": request.user_id,
        "user2_id": content["other_user_id"]
    }

    res = requests.post(CONNECTION_URL, headers=supabase_headers(), json=payload)
    if res.status_code == CONFLICT:
        return jsonify({"message": "Connection already exists"}), CONFLICT

    return jsonify({"message": "Connection created"}), CREATED


# ================================== LIST CONNECTIONS ==================================
@app.route("/connections", methods=["GET"])
@auth_user
def list_connections():
    """List all the users connection between other users"""
    # Get all connection rows for this user
    url = f"{CONNECTION_URL}?or=(user1_id.eq.{request.user_id},user2_id.eq.{request.user_id})"
    res = requests.get(url, headers=supabase_headers())
    if res.status_code != OK:
        return jsonify({"message": "Failed to load connections"}), SERVER_ERROR

    connections = res.json()
    if not connections:
        return jsonify([]), OK

    enriched = []
    for c in connections:
        other_id = c["user2_id"] if c["user1_id"] == request.user_id else c["user1_id"]

        # Get user info
        u_res = requests.get(f"{USER_URL}?user_id=eq.{other_id}", headers=supabase_headers())
        if u_res.status_code != OK or not u_res.json():
            continue
        u = u_res.json()[0]

        # Get most recent SOS event for that user
        event_res = requests.get(
            f"{EVENT_URL}?triggered_by=eq.{other_id}&order=on_at.desc&limit=1",
            headers=supabase_headers()
        )
        last_sos = "-"
        if event_res.status_code == OK and event_res.json():
            e = event_res.json()[0]
            last_sos = e.get("on_at") or "-"

        enriched.append({
            "other_user_name": u.get("user_name"),
            "other_user_email": u.get("user_email"),
            "last_sos": last_sos
        })

    return jsonify(enriched), OK


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
    
# ================================== DEVICE LOGIN ==================================
@app.route("/devices/login", methods=["POST"])
def device_login():
    """Issue a short-lived JWT for a registered device."""
    content = request.get_json()
    if "device_id" not in content:
        return jsonify({"message": "Missing device_id"}), BAD_REQUEST

    device_id = content["device_id"]

    # Verify that the device exists
    res = requests.get(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
    data = res.json()
    if not data:
        return jsonify({"message": "Device not found"}), NOT_FOUND

    # Create device token
    token = jwt.encode(
        {"device_id": device_id, "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        app.config["SECRET_KEY"], algorithm="HS256"
    )
    return jsonify({"token": token}), OK

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
# ================================== TOGGLE SOS EVENT ==================================
@app.route("/sos", methods=["POST"])
@auth_user
def toggle_sos():
    """Toggle the user's SOS state: start if inactive, stop if active."""

    now = datetime.now(timezone.utc).isoformat()

    # Check if there is an active SOS event for this user
    active_url = f"{EVENT_URL}?triggered_by=eq.{request.user_id}&handled=eq.false"
    active_res = requests.get(active_url, headers=supabase_headers())

    if active_res.status_code != OK:
        return jsonify({"message": "Failed to check SOS state"}), SERVER_ERROR

    active_events = active_res.json()

    # If active, stop it
    if active_events:
        active_event = active_events[0]
        event_id = active_event["event_id"]

        stop_data = {"off_at": now, "handled": True}
        stop_res = requests.patch(f"{EVENT_URL}?event_id=eq.{event_id}",
                                  headers=supabase_headers(), json=stop_data)

        if stop_res.status_code not in (OK, CREATED):
            return jsonify({"message": "Failed to stop SOS event"}), SERVER_ERROR

        # Mark device as offline again
        device_id = active_event.get("device_id")
        if device_id:
            device_update = {"is_online": False}
            requests.patch(f"{DEVICE_URL}?device_id=eq.{device_id}",
                           headers=supabase_headers(), json=device_update)
            
        # After stopping SOS, notify connected users
        requests.post(f"{request.host_url}sos/notify_stop/{event_id}",
                  headers={"Authorization": request.headers.get("Authorization")})    

        return jsonify({
            "message": "SOS stopped",
            "event_id": event_id,
            "active": False
        }), OK

    # Otherwise start a new SOS event
    # Check or create device automatically
    device_res = requests.get(f"{DEVICE_URL}?owner_id=eq.{request.user_id}", headers=supabase_headers())
    device_data = device_res.json()

    if device_res.status_code != OK:
        return jsonify({"message": "Failed to check devices"}), SERVER_ERROR

    if device_data:
        device_id = device_data[0]["device_id"]
    else:
        device_id = str(uuid.uuid4())
        new_device = {
            "device_id": device_id,
            "owner_id": request.user_id,
            "is_online": False,
            "last_triggered_at": None
        }
        create_res = requests.post(DEVICE_URL, headers=supabase_headers(), json=new_device)
        if create_res.status_code not in (OK, CREATED):
            return jsonify({"message": "Failed to auto-create device"}), SERVER_ERROR

    # Create the new SOS event
    event = {
        "device_id": device_id,
        "triggered_by": request.user_id,
        "on_at": now,
        "handled": False
    }

    res = requests.post(EVENT_URL, headers=supabase_headers(), json=event)
    if res.status_code not in (OK, CREATED):
        return jsonify({
            "message": "Failed to create SOS event",
            "details": res.text
        }), SERVER_ERROR

    event_info = res.json()[0]

    # Update device state
    update = {"is_online": True, "last_triggered_at": now}
    requests.patch(f"{DEVICE_URL}?device_id=eq.{device_id}",
                   headers=supabase_headers(), json=update)
    
    # Send notifications to connected users
    requests.post(f"{request.host_url}sos/notify/{event_info['event_id']}",
              headers={"Authorization": request.headers.get("Authorization")})


    return jsonify({
        "message": "SOS triggered",
        "event_id": event_info["event_id"],
        "device_id": device_id,
        "active": True
    }), CREATED

# ================================== LIST SOS EVENTS ==================================
@app.route("/sos/events", methods=["GET"])
@auth_user
def list_sos_events():
    """List SOS events filtered by user or device id (ordered by most recent)"""
    triggered_by = request.args.get("triggered_by")
    device_id = request.args.get("device_id")

    # Validate parameters
    if not triggered_by and not device_id:
        return jsonify({"message": "Missing triggered_by or device_id parameter"}), BAD_REQUEST

    # Build base URL
    if triggered_by:
        url = f"{EVENT_URL}?triggered_by=eq.{triggered_by}&order=on_at.desc"
    else:
        url = f"{EVENT_URL}?device_id=eq.{device_id}&order=on_at.desc"

    # Query Supabase REST
    res = requests.get(url, headers=supabase_headers())
    if res.status_code != OK:
        return jsonify({"message": "Failed to retrieve events"}), SERVER_ERROR

    data = res.json()
    return jsonify(data if data else []), OK

# ================================== LIST ACTIVE SOS USERS ==================================
@app.route("/sos/active", methods=["GET"])
@auth_user
def list_active_sos():
    """Return all users who currently have active SOS events."""
    res = requests.get(f"{EVENT_URL}?handled=is.false", headers=supabase_headers())
    if res.status_code != OK:
        return jsonify({"message": "Failed to fetch active SOS users"}), SERVER_ERROR

    events = res.json()
    if not events:
        return jsonify([]), OK

    active_user_ids = [e["triggered_by"] for e in events]

    # Retrieve names and emails for those users
    if not active_user_ids:
        return jsonify([]), OK

    user_query = "or=(" + ",".join([f"user_id.eq.{uid}" for uid in active_user_ids]) + ")"
    users_res = requests.get(f"{USER_URL}?{user_query}", headers=supabase_headers())

    if users_res.status_code != OK:
        return jsonify({"message": "Failed to fetch users"}), SERVER_ERROR

    return jsonify(users_res.json()), OK


#|---------------------------------------------------------------------------------------------------|
#|                                   NOTIFICATIONS ENDPOINTS                                         |                               |
#|---------------------------------------------------------------------------------------------------|
# ================================== LIST NOTIFICATIONS ==================================
@app.route("/notifications", methods=["GET"])
@auth_user
def get_notifications():
    """List notifications sent to the current user"""
    res = requests.get(f"{NOTIF_URL}?notified_user=eq.{request.user_id}", headers=supabase_headers())
    return jsonify(res.json()), OK

# ================================== NOTIFY SOS START ==================================
@app.route("/sos/notify/<uuid:event_id>", methods=["POST"])
@auth_user
def notify_sos_start(event_id):
    """Send notification to all connected users when SOS is triggered"""
    current_user = request.user_id
    now = datetime.now(timezone.utc).isoformat()

    # Get the triggering user's info
    u_res = requests.get(f"{USER_URL}?user_id=eq.{current_user}", headers=supabase_headers())
    user_info = u_res.json()[0] if u_res.status_code == OK and u_res.json() else {}
    trigger_name = user_info.get("user_name", "Unknown")
    trigger_email = user_info.get("user_email", "")

    # Find connected users
    con_res = requests.get(
        f"{CONNECTION_URL}?or=(user1_id.eq.{current_user},user2_id.eq.{current_user})",
        headers=supabase_headers()
    )
    if con_res.status_code != OK:
        return jsonify({"message": "Failed to find connections"}), SERVER_ERROR

    connections = con_res.json()
    notified_count = 0

    for conn in connections:
        other_user = conn["user2_id"] if conn["user1_id"] == current_user else conn["user1_id"]
        notif = {
            "event_id": str(event_id),
            "notified_user": other_user,
            "sent_at": now,
            "trigger_name": trigger_name,
            "trigger_email": trigger_email
        }
        requests.post(NOTIF_URL, headers=supabase_headers(), json=notif)
        notified_count += 1

    return jsonify({"message": f"Start notifications sent to {notified_count} users"}), OK

# ================================== NOTIFY SOS STOP ==================================
@app.route("/sos/notify_stop/<uuid:event_id>", methods=["POST"])
@auth_user
def notify_sos_stop(event_id):
    """Mark notifications as seen/ended when SOS is stopped"""
    now = datetime.now(timezone.utc).isoformat()

    # Mark all notifications for this event as seen
    patch_data = {"seen_at": now}
    res = requests.patch(f"{NOTIF_URL}?event_id=eq.{event_id}",
                         headers=supabase_headers(), json=patch_data)

    return jsonify({"message": "Stop notifications updated"}), OK


# ================================== MAIN ==================================
if __name__ == "__main__":
    app.run(port=8080, debug=True)