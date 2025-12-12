package gabriellopes.safesenior.app.safeseniorapp.adapters;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import java.util.List;

import gabriellopes.safesenior.app.safeseniorapp.R;
import gabriellopes.safesenior.app.safeseniorapp.models.Event;

public class EventsAdapter extends RecyclerView.Adapter<EventsAdapter.ViewHolder> {
    // List of SOS events to display
    private final List<Event> events;
    // Store events passed from the activity
    public EventsAdapter(List<Event> events) {
        this.events = events;
    }

    // Convert an ISO8601 date string into a readable format for the UI
    private String formatDate(String isoString) {
        try {
            java.time.OffsetDateTime odt = java.time.OffsetDateTime.parse(isoString);
            java.time.format.DateTimeFormatter fmt =
                    java.time.format.DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm:ss");
            return odt.toLocalDateTime().format(fmt);
        } catch (Exception e) {
            return "-";
        }
    }

    // Inflate the layout for a single event row
    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_event, parent, false);
        return new ViewHolder(v);
    }

    // Bind each event's data into the row views
    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        Event e = events.get(position);

        // Show event ID
        holder.txtEventId.setText("Event: " + e.event_id);

        // Format item display
        if (e.on_at != null) holder.txtOnAt.setText("Started: " + formatDate(e.on_at));
        else holder.txtOnAt.setText("Started: -");
        if (e.off_at != null) holder.txtOffAt.setText("Stopped: " + formatDate(e.off_at));
        else holder.txtOffAt.setText("Stopped: Active");

        // Status text
        if (!e.handled) {
            holder.txtHandled.setText("Status: Active");
            holder.txtHandled.setTextColor(android.graphics.Color.RED);
        } else if (e.handled && e.handled_by != null && !e.handled_by.isEmpty()) {
            holder.txtHandled.setText("Status: Responded by " + e.handled_by);
            holder.txtHandled.setTextColor(android.graphics.Color.parseColor("#2E7D32")); // green
        } else {
            holder.txtHandled.setText("Status: Stopped by User (No response)");
            holder.txtHandled.setTextColor(android.graphics.Color.DKGRAY);
        }

    }

    // Number of events in the list
    @Override
    public int getItemCount() {
        return events.size();
    }

    // Holds references to the TextViews inside a row
    public static class ViewHolder extends RecyclerView.ViewHolder {
        TextView txtEventId, txtOnAt, txtOffAt, txtHandled;

        // Connect UI elements from XML to Java fields
        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            txtEventId = itemView.findViewById(R.id.txtEventId);
            txtOnAt = itemView.findViewById(R.id.txtOnAt);
            txtOffAt = itemView.findViewById(R.id.txtOffAt);
            txtHandled = itemView.findViewById(R.id.txtHandled);
        }
    }
}
