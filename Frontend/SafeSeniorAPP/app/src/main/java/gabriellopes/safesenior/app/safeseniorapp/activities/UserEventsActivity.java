package gabriellopes.safesenior.app.safeseniorapp.activities;

import android.os.Bundle;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import java.util.List;

import gabriellopes.safesenior.app.safeseniorapp.R;
import gabriellopes.safesenior.app.safeseniorapp.adapters.EventsAdapter;
import gabriellopes.safesenior.app.safeseniorapp.models.Event;
import gabriellopes.safesenior.app.safeseniorapp.network.ApiClient;
import gabriellopes.safesenior.app.safeseniorapp.network.ApiInterface;
import gabriellopes.safesenior.app.safeseniorapp.network.SharedPrefHelper;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class UserEventsActivity extends AppCompatActivity {

    private RecyclerView recyclerEvents;
    private EventsAdapter adapter;
    private ApiInterface api;
    private SharedPrefHelper prefHelper;
    // Email of the user whose SOS history is being displayed
    private String selectedUserEmail;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);
        setContentView(R.layout.activity_user_events);

        // Email passed from dashboard
        selectedUserEmail = getIntent().getStringExtra("email");

        // List that will display the selected user's SOS events
        recyclerEvents = findViewById(R.id.recyclerEvents);
        recyclerEvents.setLayoutManager(new LinearLayoutManager(this));

        // Helpers for reading auth token and calling the API
        prefHelper = new SharedPrefHelper(this);
        api = ApiClient.getClient().create(ApiInterface.class);

        loadEvents();
    }

    // Load User SOS events
    private void loadEvents() {
        String token = prefHelper.getToken();
        if (token == null || selectedUserEmail == null) {
            Toast.makeText(this, "Missing email", Toast.LENGTH_SHORT).show();
            return;
        }

        api.getEvents(token, selectedUserEmail).enqueue(new Callback<List<Event>>() {
            @Override
            public void onResponse(Call<List<Event>> call, Response<List<Event>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    // Bind retrieved events to the RecyclerView
                    adapter = new EventsAdapter(response.body());
                    recyclerEvents.setAdapter(adapter);
                } else {
                    Toast.makeText(UserEventsActivity.this, "No events found", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<List<Event>> call, Throwable t) {
                Toast.makeText(UserEventsActivity.this, "Network error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }
}
