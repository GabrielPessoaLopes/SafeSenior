from flask import Flask, jsonify, request
from functools import wraps
from datetime import datetime, timezone, timedelta
import os, jwt, requests
import uuid
from dotenv import load_dotenv
import os
import hashlib

 # load variables from .env into environment
load_dotenv() 

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "default_secret_key")

# Supabase handles SQL execution automatically from REST queries
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")

# Base REST paths
SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1"
USER_URL = f"{SUPABASE_REST_URL}/user"
CONNECTION_URL = f"{SUPABASE_REST_URL}/connection"
DEVICE_URL = f"{SUPABASE_REST_URL}/sos_device"
EVENT_URL = f"{SUPABASE_REST_URL}/sos_event"
HELP_URL = f"{SUPABASE_REST_URL}/help_event"
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
#|                                      AUTH DECORATORS                                              |                               
#|---------------------------------------------------------------------------------------------------|
# ================================== USER ================================== 
def auth_user(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"message": "Token is missing"}), UNAUTHORIZED

        token = auth

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except Exception:
            return jsonify({"message": "Invalid token"}), UNAUTHORIZED

        # User token
        if "id" in data:
            request.user_id = data["id"]
            return f(*args, **kwargs)

        # Device token
        if "device_id" in data:
            dev_id = data["device_id"]
            res = requests.get(f"{DEVICE_URL}?device_id=eq.{dev_id}", headers=supabase_headers())
            dev_data = res.json()

            if not dev_data:
                return jsonify({"message": "Device not registered"}), UNAUTHORIZED

            request.user_id = dev_data[0]["owner_id"]
            return f(*args, **kwargs)

        return jsonify({"message": "Invalid token"}), UNAUTHORIZED
    return decorated


# ================================== SOS DEVICE ================================== 
def auth_device(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        content = request.get_json() or {}

        device_id = content.get("device_id")
        if not device_id:
            return jsonify({"message": "Missing device_id"}), BAD_REQUEST

        # Check device in Supabase
        res = requests.get(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
        data = res.json()

        if not data:
            return jsonify({"message": "Device not registered"}), NOT_FOUND

        # Attach owner_id so the endpoint knows who triggered it
        request.device_id = device_id
        request.user_id = data[0]["owner_id"]

        return f(*args, **kwargs)
    return decorated

#|---------------------------------------------------------------------------------------------------|
#|                                      USER ENDPOINTS                                               |                               
#|---------------------------------------------------------------------------------------------------|
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
    """Login a user"""

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
    """Get the authenticated user's profile info"""

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
    """Create a two ended connection between two users"""

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
    """List all the users connections"""

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

        # Get device id
        dev_res = requests.get(f"{DEVICE_URL}?owner_id=eq.{other_id}", headers=supabase_headers())
        dev_data = dev_res.json()
        device_id = dev_data[0]["device_id"] if dev_data else None

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
            "device_id": device_id,
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
    """Register a new SOS device and set up its ID"""

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
    """Return a temporary JWT for a registered device"""

    content = request.get_json()
    if "device_id" not in content:
        return jsonify({"message": "Missing device_id"}), BAD_REQUEST

    device_id = content["device_id"]

    # Check if device exists
    res = requests.get(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
    data = res.json()
    if not data:
        return jsonify({"message": "Device not found"}), NOT_FOUND

    # Generate token
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
    """Return device info"""

    res = requests.get(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
    data = res.json()
    if not data:
        return jsonify({"message": "Device not found"}), NOT_FOUND
    return jsonify(data[0]), OK

# ================================== GET DEVICE ONLINE ==================================
@app.route("/device/online", methods=["POST"])
def device_online():

    content = request.get_json() or {}
    device_id = content.get("device_id")
    if not device_id:
        return jsonify({"message": "Missing device_id"}), BAD_REQUEST

    # Validate device
    res = requests.get(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
    data = res.json()
    if not data:
        return jsonify({"message": "Device not registered"}), NOT_FOUND

    # UPDATE DEVICE (YOU REMOVED THIS!)
    update = {
        "is_online": True,
        "last_seen_at": datetime.now(timezone.utc).isoformat()
    }
    requests.patch(
        f"{DEVICE_URL}?device_id=eq.{device_id}",
        headers=supabase_headers(),
        json=update
    )

    # Close any active help events
    requests.patch(
        f"{HELP_URL}?device_id=eq.{device_id}&active=eq.true",
        headers=supabase_headers(),
        json={"active": False, "help_off_at": datetime.now(timezone.utc).isoformat()}
    )

    return jsonify({"message": "Device online"}), OK


# ================================== GET DEVICE OFFLINE ==================================
@app.route("/device/offline", methods=["POST"])
def device_offline():
    """Mark a device as offline."""

    content = request.get_json() or {}
    device_id = content.get("device_id")
    if not device_id:
        return jsonify({"message": "Missing device_id"}), BAD_REQUEST

    # Update offline state
    update = {"is_online": False}
    requests.patch(
        f"{DEVICE_URL}?device_id=eq.{device_id}",
        headers=supabase_headers(),
        json=update
    )
    return jsonify({"message": "Device offline"}), OK

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
def toggle_sos():
    """Toggle SOS state from app or device."""

    # Determine source (frontend (JWT) or device (device_id))
    auth_header = request.headers.get("Authorization")

    # If header (token) exists, then frontend
    if auth_header:
        # SOS triggered from frontend
        result = auth_user(lambda: None)()
        if result:
            return result
        user_id = request.user_id
        device_id = None
    # SOS alert comes from a device
    else:
        # SOS triggered from device
        result = auth_device(lambda: None)()
        if result:
            return result
        user_id = request.user_id
        device_id = request.device_id

    now = datetime.now(timezone.utc).isoformat()

    # Check for active SOS events
    active_url = f"{EVENT_URL}?triggered_by=eq.{user_id}&handled=eq.false"
    active_res = requests.get(active_url, headers=supabase_headers())
    active_events = active_res.json()

    # Stop SOS
    if active_events:
        active_event = active_events[0]
        event_id = active_event["event_id"]

        stop_data = {"off_at": now, "handled": True}
        requests.patch(f"{EVENT_URL}?event_id=eq.{event_id}",
                       headers=supabase_headers(), json=stop_data)
        
        # Disable help event automatically
        requests.patch(
            f"{HELP_URL}?device_id=eq.{device_id}&active=eq.true",
            headers=supabase_headers(),
            json={"active": False, "help_off_at": datetime.now(timezone.utc).isoformat()}
        )

        # Device-specific cleanup
        if device_id:
            requests.patch(
                f"{DEVICE_URL}?device_id=eq.{device_id}",
                headers=supabase_headers(),
                json={"is_online": False}
            )

        return jsonify({"message": "SOS stopped", "active": False}), OK

    # Start SOS (frontend only)
    if not device_id:
        d_res = requests.get(f"{DEVICE_URL}?owner_id=eq.{user_id}", headers=supabase_headers())
        d_data = d_res.json()
        if d_data:
            device_id = d_data[0]["device_id"]
        else:
            device_id = str(uuid.uuid4())
            new_device = {
                "device_id": device_id,
                "owner_id": user_id,
                "is_online": False,
                "last_triggered_at": None
            }
            requests.post(DEVICE_URL, headers=supabase_headers(), json=new_device)

    # create event
    event = {
        "device_id": device_id,
        "triggered_by": user_id,
        "on_at": now,
        "handled": False
    }

    res = requests.post(EVENT_URL, headers=supabase_headers(), json=event)
    event_info = res.json()[0]

    # update device
    requests.patch(
        f"{DEVICE_URL}?device_id=eq.{device_id}",
        headers=supabase_headers(),
        json={"is_online": True, "last_triggered_at": now}
    )

    return jsonify({
        "message": "SOS triggered",
        "active": True,
        "event_id": event_info["event_id"],
        "device_id": device_id
    }), CREATED

# ================================== LIST SOS EVENTS ==================================
@app.route("/sos/events", methods=["GET"])
@auth_user
def list_sos_events():
    """Return SOS events for a user by email."""

    triggered_email = request.args.get("triggered_email")

    if not triggered_email:
        return jsonify({"message": "Missing triggered_email parameter"}), BAD_REQUEST

    # Get user by email
    user_query = f"{USER_URL}?user_email=eq.{triggered_email}"
    user_response = requests.get(user_query, headers=supabase_headers())
    user_data = user_response.json()

    if not user_data:
        return jsonify([]), OK

    user_id = user_data[0]["user_id"]

    # Get user's SOS events
    events_query = (
        f"{EVENT_URL}?triggered_by=eq.{user_id}&order=on_at.desc"
    )
    events_response = requests.get(events_query, headers=supabase_headers())

    if events_response.status_code != OK:
        return jsonify({"message": "Failed to retrieve events"}), SERVER_ERROR

    events = events_response.json()
    return jsonify(events if events else []), OK
    
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

    # Get user details for each ID
    if not active_user_ids:
        return jsonify([]), OK

    user_query = "or=(" + ",".join([f"user_id.eq.{uid}" for uid in active_user_ids]) + ")"
    users_res = requests.get(f"{USER_URL}?{user_query}", headers=supabase_headers())

    if users_res.status_code != OK:
        return jsonify({"message": "Failed to fetch users"}), SERVER_ERROR

    return jsonify(users_res.json()), OK


#|---------------------------------------------------------------------------------------------------|
#|                                     HELP TOGGLE ENDPOINTS                                         |
#|---------------------------------------------------------------------------------------------------|
# ================================== TOGGLE HELP SIGNAL ==================================
@app.route("/help/toggle", methods=["POST"])
@auth_user
def toggle_help():
    """Toggle help_event for a device and record caregiver email."""

    content = request.get_json() or {}

    device_id = content.get("device_id")
    if not device_id:
        return jsonify({"message": "Missing device_id"}), BAD_REQUEST

    # caregiver email
    user_res = requests.get(f"{USER_URL}?user_id=eq.{request.user_id}", headers=supabase_headers())
    user_data = user_res.json()
    caregiver_email = user_data[0]["user_email"] if user_data else None

    # confirm device exists
    dev_res = requests.get(f"{DEVICE_URL}?device_id=eq.{device_id}", headers=supabase_headers())
    dev_data = dev_res.json()
    if not dev_data:
        return jsonify({"message": "Device not registered"}), NOT_FOUND

    triggered_by = dev_data[0]["owner_id"]
    now = datetime.now(timezone.utc).isoformat()

    # check active help_event
    active_url = f"{HELP_URL}?device_id=eq.{device_id}&active=eq.true"
    res = requests.get(active_url, headers=supabase_headers())
    active_events = res.json()

    # close active help_event
    if active_events:
        help_id = active_events[0]["help_id"]

        update = {
            "help_off_at": now,
            "active": False,
            "handled_by": caregiver_email
        }

        requests.patch(f"{HELP_URL}?help_id=eq.{help_id}", headers=supabase_headers(), json=update)

        # check active sos_event for this device
        sos_active_res = requests.get(
            f"{EVENT_URL}?device_id=eq.{device_id}&handled=eq.false",
            headers=supabase_headers()
        )
        sos_active = sos_active_res.json()

        # mark the sos_event as handled by this caregiver
        if sos_active:
            sos_id = sos_active[0]["event_id"]
            requests.patch(
                f"{EVENT_URL}?event_id=eq.{sos_id}",
                headers=supabase_headers(),
                json={"handled": True, "handled_by": caregiver_email}
            )

        
        return jsonify({"help": False}), OK

    # create new help_event
    new_event = {
        "device_id": device_id,
        "triggered_by": triggered_by,
        "help_on_at": now,
        "active": True,
        "handled_by": caregiver_email
    }

    created = requests.post(HELP_URL, headers=supabase_headers(), json=new_event).json()[0]

    # check active sos_event to save who responded
    sos_active_res = requests.get(
        f"{EVENT_URL}?device_id=eq.{device_id}&handled=eq.false",
        headers=supabase_headers()
    )
    sos_active = sos_active_res.json()

    # add caregiver email to the sos_event
    if sos_active:
        sos_id = sos_active[0]["event_id"]
        requests.patch(
            f"{EVENT_URL}?event_id=eq.{sos_id}",
            headers=supabase_headers(),
            json={"handled_by": caregiver_email}
        )

    return jsonify({
        "message": "Help on the way!",
        "help": True,
        "help_id": created["help_id"]
    }), CREATED

# ================================== GET HELP STATE ==================================
@app.route("/help/state/<string:device_id>", methods=["GET"])
def help_get_state(device_id):
    """"Return help state for a device."""

    active_url = f"{HELP_URL}?device_id=eq.{device_id}&active=eq.true"
    res = requests.get(active_url, headers=supabase_headers())
    events = res.json()

    return jsonify({"help": bool(events)}), OK

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

    # Get connected users
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
    """Mark notifications as seen when SOS is stopped"""

    now = datetime.now(timezone.utc).isoformat()

    # Update notification state
    patch_data = {"seen_at": now}
    res = requests.patch(f"{NOTIF_URL}?event_id=eq.{event_id}",
                         headers=supabase_headers(), json=patch_data)

    return jsonify({"message": "Stop notifications updated"}), OK

# ================================== MAIN ==================================
if __name__ == "__main__":
    #app.run(port=8080, debug=True)
    app.run(host="0.0.0.0", port=8080, debug=True)