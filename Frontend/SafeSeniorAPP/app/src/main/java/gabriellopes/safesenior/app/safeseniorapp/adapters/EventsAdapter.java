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

    private final List<Event> events;

    public EventsAdapter(List<Event> events) {
        this.events = events;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_event, parent, false);
        return new ViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        Event e = events.get(position);

        holder.txtEventId.setText("Event: " + e.event_id);
        holder.txtOnAt.setText("Started: " + (e.on_at != null ? e.on_at : "N/A"));
        holder.txtOffAt.setText("Stopped: " + (e.off_at != null ? e.off_at : "Active"));
        holder.txtHandled.setText(e.handled ? "Status: Handled" : "Status: Pending");
    }

    @Override
    public int getItemCount() {
        return events.size();
    }

    public static class ViewHolder extends RecyclerView.ViewHolder {
        TextView txtEventId, txtOnAt, txtOffAt, txtHandled;
        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            txtEventId = itemView.findViewById(R.id.txtEventId);
            txtOnAt = itemView.findViewById(R.id.txtOnAt);
            txtOffAt = itemView.findViewById(R.id.txtOffAt);
            txtHandled = itemView.findViewById(R.id.txtHandled);
        }
    }
}
