package gabriellopes.safesenior.app.safeseniorapp.network;
import android.content.Context;
import android.content.SharedPreferences;

public class SharedPrefHelper {
    private static final String PREFS_NAME = "SafeSeniorPrefs";
    private static final String TOKEN_KEY = "token";
    private static final String USER_ID_KEY = "userId";
    private final SharedPreferences prefs;

    public SharedPrefHelper(Context context) {
        prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    public void saveAuth(String token, String userId) {
        prefs.edit().putString(TOKEN_KEY, token)
                .putString(USER_ID_KEY, userId)
                .apply();
    }

    public String getToken() {
        return prefs.getString(TOKEN_KEY, null);
    }

    public String getUserId() {
        return prefs.getString(USER_ID_KEY, null);
    }

    public void clearAuth() {
        prefs.edit().clear().apply();
    }
}
