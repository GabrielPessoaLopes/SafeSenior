package gabriellopes.safesenior.app.safeseniorapp.activities;

import android.content.Intent;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.floatingactionbutton.FloatingActionButton;
import com.google.gson.JsonObject;

import java.util.List;
import gabriellopes.safesenior.app.safeseniorapp.R;
import gabriellopes.safesenior.app.safeseniorapp.adapters.ConnectionsAdapter;
import gabriellopes.safesenior.app.safeseniorapp.models.Connection;
import gabriellopes.safesenior.app.safeseniorapp.models.Notification;
import gabriellopes.safesenior.app.safeseniorapp.models.SosStartResponse;
import gabriellopes.safesenior.app.safeseniorapp.network.ApiClient;
import gabriellopes.safesenior.app.safeseniorapp.network.ApiInterface;
import gabriellopes.safesenior.app.safeseniorapp.network.SharedPrefHelper;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity {

    private android.widget.TextView sosAlertText;
    private View flashOverlay;
    private android.animation.ObjectAnimator alertBlinkAnimator;
    private RecyclerView recyclerView;
    private ConnectionsAdapter adapter;
    private FloatingActionButton sosButton;
    private boolean sosActive = false;
    private android.animation.ObjectAnimator blinkAnimator;
    private SharedPrefHelper prefHelper;
    private ApiInterface api;
    private final android.os.Handler activeRefreshHandler = new android.os.Handler();

    // Periodically refreshes the SOS status of all connections for real-time UI updates
    private final Runnable activeRefreshRunnable = new Runnable() {
        @Override
        public void run() {
            loadActiveSOS();
            activeRefreshHandler.postDelayed(this, 5000);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Force light theme because dark mode breaks visibility of SOS visuals
        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);

        // Inflate the main dashboard layout
        setContentView(R.layout.activity_main);

        // UI elements responsible for SOS blinking warnings
        sosAlertText = findViewById(R.id.sosAlertText);
        flashOverlay = findViewById(R.id.flashOverlay);

        // Load saved authentication token and user details
        prefHelper = new SharedPrefHelper(this);

        // Retrofit instance used for all API requests
        api = ApiClient.getClient().create(ApiInterface.class);

        // Main dashboard table (list of user connections)
        recyclerView = findViewById(R.id.recyclerConnections);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));

        // floating SOS button (toggle between start/stop)
        sosButton = findViewById(R.id.btnSOS);
        sosButton.setOnClickListener(v -> toggleSOS());

        // Load connections and prepare dashboard
        loadConnections();
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.menu_main, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(@NonNull MenuItem item) {
        // Logout
        if (item.getItemId() == R.id.action_logout) {
            prefHelper.clearAuth();
            startActivity(new Intent(MainActivity.this, LoginActivity.class));
            finish();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    // Populate the dashboard with all the users that the current user is connected to
    private void loadConnections() {
        String token = prefHelper.getToken();
        if (token == null) {
            Toast.makeText(this, "No token found, redirecting to login", Toast.LENGTH_SHORT).show();
            startActivity(new Intent(this, LoginActivity.class));
            finish();
            return;
        }

        api.getConnections(token).enqueue(new Callback<List<Connection>>() {
            @Override
            public void onResponse(@NonNull Call<List<Connection>> call, @NonNull Response<List<Connection>> response) {
                // If connections exist, build adapter
                if (response.isSuccessful() && response.body() != null && !response.body().isEmpty()) {
                    // Attach adapter and load initial dashboard data
                    adapter = new ConnectionsAdapter(response.body(), new ConnectionsAdapter.OnConnectionClickListener() {
                        @Override
                        public void onConnectionClick(Connection connection) {
                            // Open user SOS events history
                            Intent i = new Intent(MainActivity.this, UserEventsActivity.class);
                            i.putExtra("email", connection.user_email);
                            i.putExtra("name", connection.user_name);
                            startActivity(i);
                        }

                        @Override
                        public void onSendMessageClick(Connection c) {
                            // Help event requires the user device's ID
                            if (c.device_id == null || c.device_id.isEmpty()) {
                                Toast.makeText(MainActivity.this, "No device ID for this user", Toast.LENGTH_SHORT).show();
                                return;
                            }

                            JsonObject body = new JsonObject();
                            body.addProperty("device_id", c.device_id);
                            // Toggle help event
                            api.toggleHelp(token, body).enqueue(new Callback<Void>() {
                                @Override
                                public void onResponse(Call<Void> call, Response<Void> response) {

                                }

                                @Override
                                public void onFailure(Call<Void> call, Throwable t) {
                                    Toast.makeText(MainActivity.this, "Failed to send help", Toast.LENGTH_SHORT).show();
                                }
                            });
                        }
                    });
                    recyclerView.setAdapter(adapter);
                    loadActiveSOS();
                    loadNotifications();
                    startActiveSOSAutoRefresh();
                } else if (response.isSuccessful()) {
                    Toast.makeText(MainActivity.this, "No connections found", Toast.LENGTH_SHORT).show();
                } else {
                    String msg = "Failed: " + response.code();
                    try {
                        if (response.errorBody() != null)
                            msg += " | " + response.errorBody().string();
                    } catch (Exception ignored) {}
                    Toast.makeText(MainActivity.this, msg, Toast.LENGTH_LONG).show();
                }
            }

            @Override
            public void onFailure(@NonNull Call<List<Connection>> call, @NonNull Throwable t) {
                Toast.makeText(MainActivity.this, "Network failure: " + t.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    // Refresh dashboard SOS state
    private void loadActiveSOS() {
        String token = prefHelper.getToken();
        if (token == null || adapter == null)
            return;
        // Get the list of users who currently have an active SOS from API
        api.getActiveSosUsers(token).enqueue(new Callback<List<Connection>>() {
            @Override
            public void onResponse(Call<List<Connection>> call, Response<List<Connection>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    adapter.setActiveSOSUsers(response.body());
                }
            }

            @Override
            public void onFailure(Call<List<Connection>> call, Throwable t) {}
        });
    }

    // Display unseen notifications
    private void loadNotifications() {
        String token = prefHelper.getToken();
        if (token == null) return;

        api.getNotifications(token).enqueue(new Callback<List<Notification>>() {
            @Override
            public void onResponse(@NonNull Call<List<Notification>> call,
                                   @NonNull Response<List<Notification>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    // highlight unseen SOS alerts
                    for (Notification n : response.body()) {
                        if (n.seen_at == null && n.trigger_name != null) {
                            Toast.makeText(MainActivity.this,n.trigger_name + " triggered an SOS!",
                                    Toast.LENGTH_LONG).show();
                            if (adapter != null && n.trigger_email != null) {
                                adapter.highlightUserByEmail(n.trigger_email);
                            }
                        }
                    }
                }
            }

            @Override
            public void onFailure(@NonNull Call<List<Notification>> call, @NonNull Throwable t) {}
        });
    }

    // Keeps the dashboard updated without user interaction
    private void startActiveSOSAutoRefresh() {
        activeRefreshHandler.removeCallbacks(activeRefreshRunnable);
        activeRefreshHandler.post(activeRefreshRunnable);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        activeRefreshHandler.removeCallbacks(activeRefreshRunnable);
    }

    //  Toggle SOS (same endpoint for start and stop)
    private void toggleSOS() {
        String token = prefHelper.getToken();
        if (token == null) {
            Toast.makeText(this, "Not authenticated", Toast.LENGTH_SHORT).show();
            return;
        }

        api.toggleSos(token).enqueue(new Callback<SosStartResponse>() {
            @Override
            public void onResponse(@NonNull Call<SosStartResponse> call, @NonNull Response<SosStartResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    // Use response.active to decide if SOS was started or stopped and update UI
                    SosStartResponse sosResponse = response.body();
                    if (sosResponse.active) {
                        sosActive = true;
                        startFlashingButton();
                        Toast.makeText(MainActivity.this, "SOS TRIGGERED", Toast.LENGTH_SHORT).show();
                    } else {
                        sosActive = false;
                        stopFlashingButton();
                        Toast.makeText(MainActivity.this, "SOS STOPPED", Toast.LENGTH_SHORT).show();
                    }
                    // refresh dashboard states
                    loadActiveSOS();
                } else {
                    Toast.makeText(MainActivity.this, "Failed to toggle SOS", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(@NonNull Call<SosStartResponse> call, @NonNull Throwable t) {
                Toast.makeText(MainActivity.this, "Network error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }

    // Start all SOS visual alerts (button blink, text blink and screen overlay)
    private void startFlashingButton() {

        // Animation that repeatedly fades the SOS button in/out
        blinkAnimator = android.animation.ObjectAnimator.ofFloat(sosButton, "alpha", 1f, 0.3f);
        blinkAnimator.setDuration(500);
        blinkAnimator.setRepeatMode(android.animation.ValueAnimator.REVERSE);
        blinkAnimator.setRepeatCount(android.animation.ValueAnimator.INFINITE);
        blinkAnimator.start();

        // Turn the SOS button visibly red while active
        sosButton.setColorFilter(getColor(android.R.color.holo_red_dark));

        // Show and blink the red "SOS ALERT" label
        sosAlertText.setVisibility(View.VISIBLE);
        android.animation.ObjectAnimator alertBlink = android.animation.ObjectAnimator.ofFloat(sosAlertText, "alpha", 1f, 0.3f);
        alertBlink.setDuration(600);
        alertBlink.setRepeatMode(android.animation.ValueAnimator.REVERSE);
        alertBlink.setRepeatCount(android.animation.ValueAnimator.INFINITE);
        alertBlink.start();

        // Show the full-screen red overlay with a pulsing fade effect
        flashOverlay.setVisibility(View.VISIBLE);
        android.animation.ObjectAnimator flashAnim = android.animation.ObjectAnimator.ofFloat(flashOverlay, "alpha", 0.8f, 0f);
        flashAnim.setDuration(700);
        flashAnim.setRepeatMode(android.animation.ValueAnimator.REVERSE);
        flashAnim.setRepeatCount(android.animation.ValueAnimator.INFINITE);
        flashAnim.start();

        // Keep reference so animation can be stopped later
        alertBlinkAnimator = flashAnim;
    }

    // Stop all SOS visual alerts (button blink, text blink and screen overlay)
    private void stopFlashingButton() {
        // Stop blinking animation on the SOS button
        if (blinkAnimator != null) {
            blinkAnimator.cancel();
            sosButton.setAlpha(1f);
        }
        // Remove red tint from the button
        sosButton.clearColorFilter();

        // Stop overlay animation if active
        if (alertBlinkAnimator != null) {
            alertBlinkAnimator.cancel();
        }

        // Hide flashing UI elements
        flashOverlay.setVisibility(View.GONE);
        sosAlertText.setVisibility(View.GONE);
    }
}
