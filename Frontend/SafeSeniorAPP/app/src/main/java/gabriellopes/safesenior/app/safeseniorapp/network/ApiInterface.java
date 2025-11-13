package gabriellopes.safesenior.app.safeseniorapp.network;
import java.util.List;

import gabriellopes.safesenior.app.safeseniorapp.models.Connection;
import gabriellopes.safesenior.app.safeseniorapp.models.Device;
import gabriellopes.safesenior.app.safeseniorapp.models.Event;
import gabriellopes.safesenior.app.safeseniorapp.models.LoginRequest;
import gabriellopes.safesenior.app.safeseniorapp.models.LoginResponse;
import gabriellopes.safesenior.app.safeseniorapp.models.Notification;
import gabriellopes.safesenior.app.safeseniorapp.models.RegisterRequest;

import gabriellopes.safesenior.app.safeseniorapp.models.SosStartRequest;
import gabriellopes.safesenior.app.safeseniorapp.models.SosStartResponse;
import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.Header;
import retrofit2.http.POST;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface ApiInterface {

    // User
    @POST("login")
    Call<LoginResponse> login(@Body LoginRequest body);

    @POST("register")
    Call<ResponseBody> register(@Body RegisterRequest body);

    // Connections
    @GET("connections")
    Call<List<Connection>> getConnections(@Header("Authorization") String token);

    // Devices
    @GET("devices")
    Call<List<Device>> getDevices(@Header("Authorization") String token);

    // SOS
    @POST("sos")
    Call<SosStartResponse> toggleSos(@Header("Authorization") String token);

    @GET("sos/active")
    Call<List<Connection>> getActiveSosUsers(@Header("Authorization") String token);

    @POST("notifications/{eventId}")
    Call<Void> sendNotifications(@Header("Authorization") String token, @Path("eventId") String eventId);

    @GET("sos_event")
    Call<List<Event>> getEvents(
            @Header("Authorization") String token,
            @Query("triggered_by") String triggeredBy
    );

    @GET("/notifications")
    Call<List<Notification>> getNotifications(@Header("Authorization") String token);

}

