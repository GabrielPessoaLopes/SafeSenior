package gabriellopes.safesenior.app.safeseniorapp.models;

public class LoginRequest {
        public String user_email;
        public String user_password;

        public LoginRequest(String email, String password) {
            this.user_email = email;
            this.user_password = password;
        }
    }
