class LocalStorage {

  static String? _authToken;
  static Map<String, dynamic>? _userProfile;

  static String? getToken() => _authToken;

  static Future<void> saveToken(String token) async {
    _authToken = token;
  }

  static Future<void> clearToken() async {
    _authToken = null;
  }

  static Map<String, dynamic>? getUserProfile() => _userProfile;

  static Future<void> saveUserProfile(Map<String, dynamic> json) async {
    _userProfile = json;
  }

  static Future<void> clearUserProfile() async {
    _userProfile = null;
  }

  static Future<void> clearAll() async {
    _authToken = null;
    _userProfile = null;
  }
}
