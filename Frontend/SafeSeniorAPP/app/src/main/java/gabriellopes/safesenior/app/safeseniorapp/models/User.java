package gabriellopes.safesenior.app.safeseniorapp.models;

public class User {
    public String user_id;
    public String user_name;
    public String user_email;

    public User(String id, String name, String email) {
        this.user_id = id;
        this.user_name = name;
        this.user_email = email;
    }
}


