package gabriellopes.safesenior.app.safeseniorapp.activities;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;

import gabriellopes.safesenior.app.safeseniorapp.R;
import gabriellopes.safesenior.app.safeseniorapp.models.LoginRequest;
import gabriellopes.safesenior.app.safeseniorapp.models.LoginResponse;
import gabriellopes.safesenior.app.safeseniorapp.network.ApiClient;
import gabriellopes.safesenior.app.safeseniorapp.network.ApiInterface;
import gabriellopes.safesenior.app.safeseniorapp.network.SharedPrefHelper;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class LoginActivity extends AppCompatActivity {
    EditText emailInput, passwordInput;
    Button loginButton;
    TextView registerLink;
    SharedPrefHelper prefHelper;
    ApiInterface api;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Force light theme
        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);
        setContentView(R.layout.activity_login);

        emailInput = findViewById(R.id.inputEmail);
        passwordInput = findViewById(R.id.inputPassword);
        loginButton = findViewById(R.id.btnLogin);
        registerLink = findViewById(R.id.txtRegister);
        prefHelper = new SharedPrefHelper(this);
        api = ApiClient.getClient().create(ApiInterface.class);

        loginButton.setOnClickListener(v -> login());
        registerLink.setOnClickListener(v -> startActivity(new Intent(this, RegisterActivity.class)));
    }

    private void login() {
        String email = emailInput.getText().toString().trim();
        String password = passwordInput.getText().toString().trim();

        if (email.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Fill in all fields", Toast.LENGTH_SHORT).show();
            return;
        }

        api.login(new LoginRequest(email, password)).enqueue(new Callback<LoginResponse>() {
            @Override
            public void onResponse(Call<LoginResponse> call, Response<LoginResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    prefHelper.saveAuth(response.body().token, response.body().userId);
                    startActivity(new Intent(LoginActivity.this, MainActivity.class));
                    finish();
                } else {
                    Toast.makeText(LoginActivity.this, "Invalid credentials", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<LoginResponse> call, Throwable t) {
                Toast.makeText(LoginActivity.this, "Network error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }
}
