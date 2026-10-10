import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
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

  // Authentication screen presentation state lives with its provider so the
  // screens themselves can remain stateless.
  final loginFormKey = GlobalKey<FormState>();
  final loginEmailController = TextEditingController();
  final loginPasswordController = TextEditingController();
  final loginPasswordObscured = ValueNotifier<bool>(true);
  final registerFormKey = GlobalKey<FormState>();
  final registerNameController = TextEditingController();
  final registerEmailController = TextEditingController();
  final registerPasswordController = TextEditingController();
  final registerConfirmPasswordController = TextEditingController();
  final registerPasswordObscured = ValueNotifier<bool>(true);

  void toggleLoginPasswordVisibility() =>
      loginPasswordObscured.value = !loginPasswordObscured.value;

  void toggleRegisterPasswordVisibility() =>
      registerPasswordObscured.value = !registerPasswordObscured.value;

  void resetLoginForm() {
    loginFormKey.currentState?.reset();
    loginEmailController.clear();
    loginPasswordController.clear();
    loginPasswordObscured.value = true;
  }

  void resetRegisterForm() {
    registerFormKey.currentState?.reset();
    registerNameController.clear();
    registerEmailController.clear();
    registerPasswordController.clear();
    registerConfirmPasswordController.clear();
    registerPasswordObscured.value = true;
  }

  AuthProvider({ApiClient? apiClient, SupabaseClient? supabaseClient})
      : _apiClient = apiClient ?? ApiClient(),
        _supabase = supabaseClient ?? Supabase.instance.client;

  UserModel? get currentUser => _currentUser;
  String? get token {
    final session = _supabase.auth.currentSession;
    if (session != null && !session.isExpired) {
      _token = session.accessToken;
    }
    return _token;
  }
  bool get isAuthenticated => token != null && _currentUser != null;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get errorMessage => _errorMessage;

  /// Restores saved session token and user profile
  Future<bool> checkAuthStatus() async {
    _isLoading = true;
    notifyListeners();

    try {
      var session = _supabase.auth.currentSession;
      var user = _supabase.auth.currentUser;

      if (session != null && session.isExpired) {
        try {
          final res = await _supabase.auth.refreshSession();
          session = res.session;
          user = res.user;
        } catch (_) {}
      }

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

      // Check SharedPreferences persistence backup if Supabase session memory was cleared
      final savedToken = await LocalStorage.restoreToken();
      final savedProfile = await LocalStorage.restoreUserProfile();

      if (savedToken != null && savedToken.isNotEmpty && savedProfile != null) {
        _token = savedToken;
        _currentUser = UserModel.fromJson(savedProfile);
        _errorMessage = null;
        _isInitialized = true;
        _isLoading = false;
        notifyListeners();
        return true;
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
        final msg = e.message.toLowerCase();
        if (msg.contains('invalid login credentials') || msg.contains('invalid_credentials')) {
          _errorMessage = 'Invalid email or password. Please check your credentials and try again.';
        } else if (msg.contains('email not confirmed')) {
          _errorMessage = 'Email address has not been confirmed. Please check your inbox for the confirmation link.';
        } else {
          _errorMessage = e.message;
        }
      } else if (e is ApiException) {
        _errorMessage = e.message;
      } else {
        _errorMessage = 'Login failed. Please check your network connection and try again.';
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

      var user = authRes.user;
      var session = authRes.session;

      if (user == null) {
        throw ApiException(message: 'Registration failed: Could not create user account.');
      }

      // If Supabase has immediate session creation (or auto-confirm in dev)
      if (session == null) {
        try {
          final signRes = await _supabase.auth.signInWithPassword(
            email: cleanEmail,
            password: cleanPassword,
          );
          session = signRes.session;
          user = signRes.user ?? user;
        } catch (_) {}
      }

      final currentUserObj = user;
      if (session != null && currentUserObj != null) {
        _token = session.accessToken;
        final userName = (currentUserObj.userMetadata?['name'] as String?) ?? cleanName;
        final userMap = {
          'id': currentUserObj.id,
          'email': currentUserObj.email ?? cleanEmail,
          'name': userName,
          'created_at': currentUserObj.createdAt,
        };

        _currentUser = UserModel.fromJson(userMap);
        await LocalStorage.saveUserProfile(userMap);
        await LocalStorage.saveToken(_token!);

        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = 'Registration successful! A confirmation email has been sent to $cleanEmail. Please verify your email before signing in.';
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      if (e is AuthException) {
        final msg = e.message.toLowerCase();
        if (msg.contains('user already registered') || msg.contains('already exists') || msg.contains('already registered')) {
          _errorMessage = 'This email address is already registered. Please sign in or reset your password.';
        } else {
          _errorMessage = e.message;
        }
      } else if (e is ApiException) {
        _errorMessage = e.message;
      } else {
        _errorMessage = 'Registration failed. Please check your network connection and try again.';
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

  @override
  void dispose() {
    loginEmailController.dispose();
    loginPasswordController.dispose();
    loginPasswordObscured.dispose();
    registerNameController.dispose();
    registerEmailController.dispose();
    registerPasswordController.dispose();
    registerConfirmPasswordController.dispose();
    registerPasswordObscured.dispose();
    super.dispose();
  }
}
