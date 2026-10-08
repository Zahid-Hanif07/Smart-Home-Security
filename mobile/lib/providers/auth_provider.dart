import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide LocalStorage;
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/core/storage/local_storage.dart';
import 'package:mobile/models/user_model.dart';

/// Centralized Authentication Provider
/// Responsible for: login, register, logout, session restoration, user state, and auth errors via Supabase Auth.
class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  final SupabaseClient _supabase;

  UserModel? _currentUser;
  String? _token;
  bool _isLoading = false;
  bool _isInitialized = false;
  String? _errorMessage;

  AuthProvider({ApiClient? apiClient, SupabaseClient? supabaseClient})
      : _apiClient = apiClient ?? ApiClient(),
        _supabase = supabaseClient ?? Supabase.instance.client;

  UserModel? get currentUser => _currentUser;
  String? get token => _token;
  bool get isAuthenticated => _token != null && _currentUser != null;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get errorMessage => _errorMessage;

  /// Restores saved session token and user profile
  Future<bool> checkAuthStatus() async {
    _isLoading = true;
    notifyListeners();

    try {
      final session = _supabase.auth.currentSession;
      final user = _supabase.auth.currentUser;

      if (session != null && user != null && !session.isExpired) {
        _token = session.accessToken;
        final userName = (user.userMetadata?['name'] as String?) ??
            (user.email?.contains('@') == true ? user.email!.split('@').first : 'User');
        final userMap = {
          'id': user.id,
          'email': user.email ?? '',
          'name': userName,
          'created_at': user.createdAt,
        };
        _currentUser = UserModel.fromJson(userMap);
        await LocalStorage.saveToken(_token!);
        await LocalStorage.saveUserProfile(userMap);

        _errorMessage = null;
        _isInitialized = true;
        _isLoading = false;
        notifyListeners();
        return true;
      }

      final savedToken = LocalStorage.getToken();
      if (savedToken != null && savedToken.isNotEmpty) {
        _token = savedToken;
        final cachedProfile = LocalStorage.getUserProfile();
        if (cachedProfile != null) {
          _currentUser = UserModel.fromJson(cachedProfile);
          _isInitialized = true;
          _isLoading = false;
          notifyListeners();
          return true;
        }
      }

      await logout();
      _isInitialized = true;
      return false;
    } catch (_) {
      await logout();
      _isInitialized = true;
      return false;
    } finally {
      _isInitialized = true;
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Login with email and password via Supabase Auth
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

      final authRes = await _supabase.auth.signInWithPassword(
        email: cleanEmail,
        password: cleanPassword,
      );

      final session = authRes.session;
      final user = authRes.user;

      if (session == null || user == null) {
        throw ApiException(message: 'Login failed: Could not obtain authenticated session.');
      }

      final token = session.accessToken;
      final userName = (user.userMetadata?['name'] as String?) ??
          (user.email?.contains('@') == true ? user.email!.split('@').first : 'User');

      final userMap = {
        'id': user.id,
        'email': user.email ?? cleanEmail,
        'name': userName,
        'created_at': user.createdAt,
      };

      _token = token;
      _currentUser = UserModel.fromJson(userMap);

      await LocalStorage.saveToken(token);
      await LocalStorage.saveUserProfile(userMap);

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      if (e is AuthException) {
        _errorMessage = e.message;
      } else if (e is ApiException) {
        _errorMessage = e.message;
      } else {
        _errorMessage = 'Login failed: ${e.toString()}';
      }
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Register new user profile via Supabase Auth
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

      final authRes = await _supabase.auth.signUp(
        email: cleanEmail,
        password: cleanPassword,
        data: {'name': cleanName},
      );

      final user = authRes.user;
      final session = authRes.session;

      if (user == null) {
        throw ApiException(message: 'Registration failed: Could not create Supabase Auth user.');
      }

      final token = session?.accessToken ?? '';
      final userName = (user.userMetadata?['name'] as String?) ?? cleanName;

      final userMap = {
        'id': user.id,
        'email': user.email ?? cleanEmail,
        'name': userName,
        'created_at': user.createdAt,
      };

      _currentUser = UserModel.fromJson(userMap);
      await LocalStorage.saveUserProfile(userMap);

      if (token.isNotEmpty) {
        _token = token;
        await LocalStorage.saveToken(token);
      }

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      if (e is AuthException) {
        _errorMessage = e.message;
      } else if (e is ApiException) {
        _errorMessage = e.message;
      } else {
        _errorMessage = 'Registration failed: ${e.toString()}';
      }
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  /// Logout and clear session
  Future<void> logout() async {
    try {
      await _supabase.auth.signOut();
    } catch (_) {}

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
