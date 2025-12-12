package gabriellopes.safesenior.app.safeseniorapp.models;

public class Event {
    public String event_id;
    public String device_id;
    public String triggered_by;
    public String on_at;
    public String off_at;
    public boolean handled;
    public String handled_by;   // null or "email@example.com"
}
