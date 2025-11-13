package gabriellopes.safesenior.app.safeseniorapp.adapters;

import android.animation.ObjectAnimator;
import android.animation.ValueAnimator;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;

import gabriellopes.safesenior.app.safeseniorapp.R;
import gabriellopes.safesenior.app.safeseniorapp.models.Connection;

public class ConnectionsAdapter extends RecyclerView.Adapter<ConnectionsAdapter.ViewHolder> {

    // -------------------------------------------------------------------------
    // INTERFACE
    // -------------------------------------------------------------------------
    public interface OnConnectionClickListener {
        void onConnectionClick(Connection connection);
        void onSendMessageClick(Connection connection);
    }

    // -------------------------------------------------------------------------
    // FIELDS
    // -------------------------------------------------------------------------
    private final List<Connection> connections;
    private final OnConnectionClickListener listener;
    private final List<String> activeSosEmails = new ArrayList<>();

    // -------------------------------------------------------------------------
    // CONSTRUCTOR
    // -------------------------------------------------------------------------
    public ConnectionsAdapter(List<Connection> connections, OnConnectionClickListener listener) {
        this.connections = connections;
        this.listener = listener;
    }

    // -------------------------------------------------------------------------
    // VIEW HOLDER
    // -------------------------------------------------------------------------
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

    // -------------------------------------------------------------------------
    // ADAPTER METHODS
    // -------------------------------------------------------------------------
    @NonNull
    @Override
    public ConnectionsAdapter.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_connection, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ConnectionsAdapter.ViewHolder holder, int position) {
        Connection connection = connections.get(position);

        holder.name.setText(connection.user_name);
        holder.email.setText(connection.user_email);

        // Default text
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

            ObjectAnimator animator = ObjectAnimator.ofFloat(holder.itemView, "alpha", 1f, 0.3f);
            animator.setDuration(600);
            animator.setRepeatMode(ValueAnimator.REVERSE);
            animator.setRepeatCount(ValueAnimator.INFINITE);
            animator.start();

            // Store animator reference so we can cancel it later
            holder.itemView.setTag(animator);

            holder.btnMessage.setOnClickListener(v -> listener.onSendMessageClick(connection));
        } else {
            // Reset to default appearance
            holder.itemView.setBackgroundColor(Color.WHITE);
            holder.lastSos.setTextColor(Color.BLACK);
            holder.btnMessage.setVisibility(View.GONE);
            holder.itemView.setAlpha(1f);
            holder.itemView.setTag(null);
        }

        holder.itemView.setOnClickListener(v -> listener.onConnectionClick(connection));
    }


    @Override
    public int getItemCount() {
        return connections != null ? connections.size() : 0;
    }

    // -------------------------------------------------------------------------
    // SOS STATE UPDATER
    // -------------------------------------------------------------------------
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

    public void highlightUserByEmail(String email) {
        if (email == null) return;
        if (!activeSosEmails.contains(email)) {
            activeSosEmails.add(email);
            notifyDataSetChanged();
        }
    }

}
