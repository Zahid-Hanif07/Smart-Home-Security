import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class LocalStorage {
  static const String _keyOnboardingCompleted = 'otto_onboarding_completed';
  static const String _keyAuthToken = 'otto_auth_token';
  static const String _keyUserProfile = 'otto_user_profile';

  static String? _authToken;
  static Map<String, dynamic>? _userProfile;
  static bool? _onboardingCompletedCache;

  static String? getToken() => _authToken;

  static Future<String?> restoreToken() async {
    if (_authToken != null) return _authToken;
    try {
      final prefs = await SharedPreferences.getInstance();
      _authToken = prefs.getString(_keyAuthToken);
      return _authToken;
    } catch (_) {
      return null;
    }
  }

  static Future<void> saveToken(String token) async {
    _authToken = token;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_keyAuthToken, token);
    } catch (_) {}
  }

  static Future<void> clearToken() async {
    _authToken = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_keyAuthToken);
    } catch (_) {}
  }

  static Map<String, dynamic>? getUserProfile() => _userProfile;

  static Future<Map<String, dynamic>?> restoreUserProfile() async {
    if (_userProfile != null) return _userProfile;
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = prefs.getString(_keyUserProfile);
      if (str != null && str.isNotEmpty) {
        _userProfile = jsonDecode(str) as Map<String, dynamic>;
        return _userProfile;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  static Future<void> saveUserProfile(Map<String, dynamic> json) async {
    _userProfile = json;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_keyUserProfile, jsonEncode(json));
    } catch (_) {}
  }

  static Future<void> clearUserProfile() async {
    _userProfile = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_keyUserProfile);
    } catch (_) {}
  }

  static Future<bool> isOnboardingCompleted() async {
    if (_onboardingCompletedCache != null) {
      return _onboardingCompletedCache!;
    }
    try {
      final prefs = await SharedPreferences.getInstance();
      _onboardingCompletedCache = prefs.getBool(_keyOnboardingCompleted) ?? false;
      return _onboardingCompletedCache!;
    } catch (_) {
      return _onboardingCompletedCache ?? false;
    }
  }

  static Future<void> setOnboardingCompleted(bool value) async {
    _onboardingCompletedCache = value;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_keyOnboardingCompleted, value);
    } catch (_) {}
  }

  static Future<void> clearAll() async {
    _authToken = null;
    _userProfile = null;
    _onboardingCompletedCache = false;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_keyAuthToken);
      await prefs.remove(_keyUserProfile);
      await prefs.remove(_keyOnboardingCompleted);
    } catch (_) {}
  }
}
