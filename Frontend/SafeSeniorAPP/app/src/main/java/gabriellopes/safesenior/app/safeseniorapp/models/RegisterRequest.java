package gabriellopes.safesenior.app.safeseniorapp.models;

public class RegisterRequest {
        public String user_name;
        public String user_email;
        public String user_password;

        public RegisterRequest(String name, String email, String password) {
            this.user_name = name;
            this.user_email = email;
            this.user_password = password;
        }
    }
