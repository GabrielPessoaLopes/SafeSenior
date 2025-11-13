package gabriellopes.safesenior.app.safeseniorapp.models;

import com.google.gson.annotations.SerializedName;

public class Connection {
    @SerializedName(value = "user_name", alternate = {"other_user_name"})
    public String user_name;

    @SerializedName(value = "user_email", alternate = {"other_user_email"})
    public String user_email;

    @SerializedName("last_sos")
    public String last_sos;
}
