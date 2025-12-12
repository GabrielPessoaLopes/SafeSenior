package gabriellopes.safesenior.app.safeseniorapp.adapters;

import android.animation.ObjectAnimator;
import android.animation.ValueAnimator;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

import gabriellopes.safesenior.app.safeseniorapp.R;
import gabriellopes.safesenior.app.safeseniorapp.models.Connection;

public class ConnectionsAdapter extends RecyclerView.Adapter<ConnectionsAdapter.ViewHolder> {

    // Handle UI actions from each row (item click + respond button)
    public interface OnConnectionClickListener {
        void onConnectionClick(Connection connection);
        void onSendMessageClick(Connection connection);
    }

    // List of all connections displayed in the RecyclerView
    private final List<Connection> connections;
    // Handle actions when the user clicks anything
    private final OnConnectionClickListener listener;
    // Stores the emails of users who currently have an active SOS
    private final List<String> activeSosEmails = new ArrayList<>();

    // Receives connection list
    public ConnectionsAdapter(List<Connection> connections, OnConnectionClickListener listener) {
        this.connections = connections;
        this.listener = listener;
    }

    // Holds references to each row's UI components
    public static class ViewHolder extends RecyclerView.ViewHolder {
        TextView name, email, lastSos;
        android.widget.Button btnMessage;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            name = itemView.findViewById(R.id.txtName);
            email = itemView.findViewById(R.id.txtEmail);
            lastSos = itemView.findViewById(R.id.txtLastSos);
            btnMessage = itemView.findViewById(R.id.btnMessage);
        }
    }

    // Create a new inflated row layout
    @NonNull
    @Override
    public ConnectionsAdapter.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_connection, parent, false);
        return new ViewHolder(view);
    }

    // Bind connection info + SOS UI state to a row
    @Override
    public void onBindViewHolder(@NonNull ConnectionsAdapter.ViewHolder holder, int position) {
        Connection connection = connections.get(position);

        // Basic info
        holder.name.setText(connection.user_name);
        holder.email.setText(connection.user_email);

        // Format last SOS timestamp if available
        if (connection.last_sos != null && !connection.last_sos.equals("-")) {
            try {
                java.time.ZonedDateTime zdt = java.time.ZonedDateTime.parse(connection.last_sos);
                java.time.format.DateTimeFormatter fmt =
                        java.time.format.DateTimeFormatter.ofPattern("dd-MM-yyyy   HH:mm");
                String formatted = zdt.toLocalDateTime().format(fmt);
                holder.lastSos.setText("Last SOS: " + formatted);
            } catch (Exception e) {
                holder.lastSos.setText("Last SOS: -");
            }
        } else {
            holder.lastSos.setText("Last SOS: -");
        }
        // Check if current connection has an active SOS
        boolean isActiveSOS = activeSosEmails.contains(connection.user_email);

        // Cancel any previous animator tied to this holder
        if (holder.itemView.getTag() instanceof ObjectAnimator) {
            ((ObjectAnimator) holder.itemView.getTag()).cancel();
            holder.itemView.setAlpha(1f);
        }

        if (isActiveSOS) {
            // Highlight and blink
            holder.itemView.setBackgroundColor(Color.parseColor("#FFCDD2"));
            holder.lastSos.setText("ACTIVE SOS!");
            holder.lastSos.setTextColor(Color.RED);
            holder.btnMessage.setVisibility(View.VISIBLE);

            // Blink the entire row
            ObjectAnimator animator = ObjectAnimator.ofFloat(holder.itemView, "alpha", 1f, 0.3f);
            animator.setDuration(600);
            animator.setRepeatMode(ValueAnimator.REVERSE);
            animator.setRepeatCount(ValueAnimator.INFINITE);
            animator.start();
            holder.itemView.setTag(animator);

            // Button shows state based on user "on the way" flag
            if (connection.isOnTheWay())
                holder.btnMessage.setText("Cancel");
            else
                holder.btnMessage.setText("Respond");

            holder.btnMessage.setOnClickListener(v -> {
                // Toggle "respond" button state
                connection.setOnTheWay(!connection.isOnTheWay());
                // Update UI to match state
                if (connection.isOnTheWay()) {
                    holder.btnMessage.setText("Cancel");
                }else {
                    holder.btnMessage.setText("Respond");
                }
                listener.onSendMessageClick(connection);
            });
        } else {
            // Reset to default appearance
            connection.setOnTheWay(false);
            holder.itemView.setBackgroundColor(Color.WHITE);
            holder.lastSos.setTextColor(Color.BLACK);
            holder.btnMessage.setVisibility(View.GONE);
            holder.itemView.setAlpha(1f);
            holder.itemView.setTag(null);
        }

        // Clicking the row opens event history
        holder.itemView.setOnClickListener(v -> listener.onConnectionClick(connection));
    }

    // How many rows to show
    @Override
    public int getItemCount() {
        return connections != null ? connections.size() : 0;
    }

    // Replace active SOS list and refresh UI
    public void setActiveSOSUsers(List<Connection> activeUsers) {
        activeSosEmails.clear();
        if (activeUsers != null) {
            for (Connection u : activeUsers) {
                if (u.user_email != null) {
                    activeSosEmails.add(u.user_email);
                }
            }
        }
        notifyDataSetChanged();
    }

    // Mark one user as active SOS (triggered by notification)
    public void highlightUserByEmail(String email) {
        if (email == null) return;
        if (!activeSosEmails.contains(email)) {
            activeSosEmails.add(email);
            notifyDataSetChanged();
        }
    }

}
