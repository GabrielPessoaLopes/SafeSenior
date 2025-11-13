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
    private String caredUserId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Force light theme
        AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO);
        setContentView(R.layout.activity_user_events);

        caredUserId = getIntent().getStringExtra("USER_ID");
        recyclerEvents = findViewById(R.id.recyclerEvents);
        recyclerEvents.setLayoutManager(new LinearLayoutManager(this));

        prefHelper = new SharedPrefHelper(this);
        api = ApiClient.getClient().create(ApiInterface.class);

        loadEvents();
    }

    private void loadEvents() {
        String token = prefHelper.getToken();
        if (token == null || caredUserId == null) {
            Toast.makeText(this, "Invalid session", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        api.getEvents("Bearer " + token, caredUserId).enqueue(new Callback<List<Event>>() {
            @Override
            public void onResponse(Call<List<Event>> call, Response<List<Event>> response) {
                if (response.isSuccessful() && response.body() != null) {
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
