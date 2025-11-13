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

    private final android.os.Handler sosToastHandler = new android.os.Handler();
    private final Runnable sosToastRunnable = new Runnable() {
        @Override
        public void run() {
            if (sosActive) {
                Toast.makeText(MainActivity.this, "SOS TRIGGERED", Toast.LENGTH_SHORT).show();
                sosToastHandler.postDelayed(this, 1000);
            }
        }
    };

    private final android.os.Handler activeRefreshHandler = new android.os.Handler();
    private final Runnable activeRefreshRunnable = new Runnable() {
        @Override
        public void run() {
            loadActiveSOS();
            activeRefreshHandler.postDelayed(this, 5000); // refresh every 5s
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);
        setContentView(R.layout.activity_main);

        sosAlertText = findViewById(R.id.sosAlertText);
        flashOverlay = findViewById(R.id.flashOverlay);

        prefHelper = new SharedPrefHelper(this);
        api = ApiClient.getClient().create(ApiInterface.class);

        recyclerView = findViewById(R.id.recyclerConnections);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));

        sosButton = findViewById(R.id.btnSOS);
        sosButton.setOnClickListener(v -> toggleSOS());

        loadConnections();
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.menu_main, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(@NonNull MenuItem item) {
        if (item.getItemId() == R.id.action_logout) {
            prefHelper.clearAuth();
            startActivity(new Intent(MainActivity.this, LoginActivity.class));
            finish();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

    // -------------------------------------------------------------------------
    // LOAD CONNECTIONS (Dashboard Table)
    // -------------------------------------------------------------------------
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
                if (response.isSuccessful() && response.body() != null && !response.body().isEmpty()) {

                    adapter = new ConnectionsAdapter(response.body(), new ConnectionsAdapter.OnConnectionClickListener() {
                        @Override
                        public void onConnectionClick(Connection connection) {
                            Intent i = new Intent(MainActivity.this, UserEventsActivity.class);
                            i.putExtra("USER_EMAIL", connection.user_email);
                            i.putExtra("USER_NAME", connection.user_name);
                            startActivity(i);
                        }

                        @Override
                        public void onSendMessageClick(Connection connection) {
                            Toast.makeText(MainActivity.this, "Message sent to " + connection.user_name, Toast.LENGTH_SHORT).show();
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

    private void loadActiveSOS() {
        String token = prefHelper.getToken();
        if (token == null || adapter == null) return;

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

    private void loadNotifications() {
        String token = prefHelper.getToken();
        if (token == null) return;

        api.getNotifications(token).enqueue(new Callback<List<Notification>>() {
            @Override
            public void onResponse(@NonNull Call<List<Notification>> call,
                                   @NonNull Response<List<Notification>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    for (Notification n : response.body()) {
                        if (n.seen_at == null && n.trigger_name != null) {
                            Toast.makeText(MainActivity.this,
                                    "⚠️ " + n.trigger_name + " triggered an SOS!",
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

    private void startActiveSOSAutoRefresh() {
        activeRefreshHandler.removeCallbacks(activeRefreshRunnable);
        activeRefreshHandler.post(activeRefreshRunnable);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        activeRefreshHandler.removeCallbacks(activeRefreshRunnable);
    }

    // -------------------------------------------------------------------------
    // TOGGLE SOS (start/stop same endpoint)
    // -------------------------------------------------------------------------
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
                    loadActiveSOS(); // refresh dashboard states
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

    // -------------------------------------------------------------------------
    // SOS VISUAL FEEDBACK (blinking button, overlay, and text)
    // -------------------------------------------------------------------------
    private void startFlashingButton() {
        blinkAnimator = android.animation.ObjectAnimator.ofFloat(sosButton, "alpha", 1f, 0.3f);
        blinkAnimator.setDuration(500);
        blinkAnimator.setRepeatMode(android.animation.ValueAnimator.REVERSE);
        blinkAnimator.setRepeatCount(android.animation.ValueAnimator.INFINITE);
        blinkAnimator.start();

        sosButton.setColorFilter(getColor(android.R.color.holo_red_dark));

        sosAlertText.setVisibility(View.VISIBLE);
        android.animation.ObjectAnimator alertBlink = android.animation.ObjectAnimator.ofFloat(sosAlertText, "alpha", 1f, 0.3f);
        alertBlink.setDuration(600);
        alertBlink.setRepeatMode(android.animation.ValueAnimator.REVERSE);
        alertBlink.setRepeatCount(android.animation.ValueAnimator.INFINITE);
        alertBlink.start();

        flashOverlay.setVisibility(View.VISIBLE);
        android.animation.ObjectAnimator flashAnim = android.animation.ObjectAnimator.ofFloat(flashOverlay, "alpha", 0.8f, 0f);
        flashAnim.setDuration(700);
        flashAnim.setRepeatMode(android.animation.ValueAnimator.REVERSE);
        flashAnim.setRepeatCount(android.animation.ValueAnimator.INFINITE);
        flashAnim.start();
        alertBlinkAnimator = flashAnim;
    }

    private void stopFlashingButton() {
        if (blinkAnimator != null) {
            blinkAnimator.cancel();
            sosButton.setAlpha(1f);
        }
        sosButton.clearColorFilter();

        if (alertBlinkAnimator != null) {
            alertBlinkAnimator.cancel();
        }

        flashOverlay.setVisibility(View.GONE);
        sosAlertText.setVisibility(View.GONE);
    }
}
