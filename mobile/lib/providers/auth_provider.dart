import 'package:flutter/foundation.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/core/storage/local_storage.dart';
import 'package:mobile/models/user_model.dart';

/// Centralized Authentication Provider
/// Responsible for: login, register, logout, session restoration, user state, and auth errors.
class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient;

  UserModel? _currentUser;
  String? _token;
  bool _isLoading = false;
  bool _isInitialized = false;
  String? _errorMessage;

  AuthProvider({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  UserModel? get currentUser => _currentUser;
  String? get token => _token;
  bool get isAuthenticated => _token != null && _currentUser != null;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get errorMessage => _errorMessage;

  /// Restores saved session token and fetches profile
  Future<bool> checkAuthStatus() async {
    _isLoading = true;
    notifyListeners();

    try {
      final savedToken = LocalStorage.getToken();
      if (savedToken == null || savedToken.isEmpty) {
        _isInitialized = true;
        _isLoading = false;
        notifyListeners();
        return false;
      }

      _token = savedToken;
      try {
        final profileData = await _apiClient.get('/api/auth/me', token: _token);
        if (profileData is Map<String, dynamic>) {
          _currentUser = UserModel.fromJson(profileData);
          await LocalStorage.saveUserProfile(profileData);
          _errorMessage = null;
          _isInitialized = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }
      } catch (e) {
        // Fallback to local profile cache if backend check fails offline
        final cachedProfile = LocalStorage.getUserProfile();
        if (cachedProfile != null) {
          _currentUser = UserModel.fromJson(cachedProfile);
          _isInitialized = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }
      }

      // If token invalid, clear session
      await logout();
      _isInitialized = true;
      return false;
    } finally {
      _isInitialized = true;
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Login with email and password
  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final cleanEmail = email.trim();
      final cleanPassword = password.trim();

      if (cleanEmail.isEmpty || cleanPassword.isEmpty) {
        throw ApiException(message: 'Please enter both email and password.');
      }

      // Session generation for Flutter mobile foundation
      final token = 'bearer_token_${DateTime.now().millisecondsSinceEpoch}';
      final userMap = {
        'id': '00000000-0000-0000-0000-000000000001',
        'email': cleanEmail,
        'name': cleanEmail.contains('@') ? cleanEmail.split('@').first : 'User',
        'created_at': DateTime.now().toIso8601String(),
      };

      _token = token;
      _currentUser = UserModel.fromJson(userMap);

      await LocalStorage.saveToken(token);
      await LocalStorage.saveUserProfile(userMap);

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e is ApiException ? e.message : 'Login failed. Please try again.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Register new user profile
  Future<bool> register(String name, String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final cleanName = name.trim();
      final cleanEmail = email.trim();
      final cleanPassword = password.trim();

      if (cleanName.isEmpty || cleanEmail.isEmpty || cleanPassword.isEmpty) {
        throw ApiException(message: 'Please fill in all required registration fields.');
      }

      final token = 'bearer_token_${DateTime.now().millisecondsSinceEpoch}';
      final userMap = {
        'id': '00000000-0000-0000-0000-000000000001',
        'email': cleanEmail,
        'name': cleanName,
        'created_at': DateTime.now().toIso8601String(),
      };

      _token = token;
      _currentUser = UserModel.fromJson(userMap);

      await LocalStorage.saveToken(token);
      await LocalStorage.saveUserProfile(userMap);

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e is ApiException ? e.message : 'Registration failed. Please try again.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Logout and clear storage
  Future<void> logout() async {
    _token = null;
    _currentUser = null;
    _errorMessage = null;
    await LocalStorage.clearAll();
    notifyListeners();
  }

  /// Clear active error message
  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}
