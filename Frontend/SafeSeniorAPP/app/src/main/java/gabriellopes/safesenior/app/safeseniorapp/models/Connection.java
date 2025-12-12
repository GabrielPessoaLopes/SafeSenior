package gabriellopes.safesenior.app.safeseniorapp.models;

import com.google.gson.annotations.SerializedName;

public class Connection {
    @SerializedName(value = "user_name", alternate = {"other_user_name"})
    public String user_name;

    @SerializedName(value = "user_email", alternate = {"other_user_email"})
    public String user_email;

    @SerializedName("last_sos")
    public String last_sos;

    @SerializedName("device_id")
    public String device_id;

    private boolean onTheWay = false;

    public boolean isOnTheWay() { return onTheWay; }
    public void setOnTheWay(boolean value) { this.onTheWay = value; }


}
