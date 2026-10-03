import 'package:flutter/foundation.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/models/home_model.dart';
import 'package:mobile/models/security_log_model.dart';

enum SecurityStatusState {
  secure,
  alert,
  unknownActivity,
  offline,
}

class HomeProvider extends ChangeNotifier {
  final ApiClient _apiClient;

  List<HomeModel> _homes = [];
  HomeModel? _currentHome;
  List<SecurityLogModel> _recentEvents = [];
  bool _isBackendConnected = false;
  bool _isCheckingBackend = false;
  bool _isLoading = false;
  bool _isRefreshing = false;
  String? _errorMessage;

  HomeProvider({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  List<HomeModel> get homes => List.unmodifiable(_homes);
  HomeModel? get currentHome => _currentHome;
  List<SecurityLogModel> get recentEvents => List.unmodifiable(_recentEvents);
  bool get isBackendConnected => _isBackendConnected;
  bool get isCheckingBackend => _isCheckingBackend;
  bool get isLoading => _isLoading;
  bool get isRefreshing => _isRefreshing;
  String? get errorMessage => _errorMessage;

  SecurityStatusState get securityStatus {
    if (!_isBackendConnected) {
      return SecurityStatusState.offline;
    }
    if (_recentEvents.any((e) => e.eventType.toLowerCase() == 'unknown_person' || e.isAuthorized == false)) {
      return SecurityStatusState.alert;
    }
    if (_recentEvents.any((e) => e.eventType.toLowerCase() == 'motion_detected')) {
      return SecurityStatusState.unknownActivity;
    }
    return SecurityStatusState.secure;
  }

  /// Check backend connectivity health endpoint
  Future<bool> checkBackendHealth() async {
    _isCheckingBackend = true;
    notifyListeners();

    try {
      final isOnline = await _apiClient.checkHealth();
      _isBackendConnected = isOnline;
      _isCheckingBackend = false;
      notifyListeners();
      return isOnline;
    } catch (_) {
      _isBackendConnected = false;
      _isCheckingBackend = false;
      notifyListeners();
      return false;
    }
  }

  /// Fetch homes for user, auto-creating a primary home if none exists
  Future<void> fetchHomes(String? token) async {
    _errorMessage = null;

    try {
      final responseData = await _apiClient.get('/api/homes', token: token);
      if (responseData is List) {
        _homes = responseData
            .map((item) => HomeModel.fromJson(item as Map<String, dynamic>))
            .toList();

        if (_homes.isNotEmpty) {
          _currentHome = _homes.first;
        } else if (token != null && token.isNotEmpty) {
          // Auto-create default primary home if user has none
          try {
            final newHomeData = await _apiClient.post(
              '/api/homes',
              token: token,
              body: {'name': 'Main Residence', 'address': 'Primary Location'},
            );
            if (newHomeData is Map<String, dynamic>) {
              final newHome = HomeModel.fromJson(newHomeData);
              _homes = [newHome];
              _currentHome = newHome;
            }
          } catch (_) {
            // Ignore auto-create failure if offline/restricted
          }
        }
      }
    } catch (e) {
      _errorMessage = e is ApiException ? e.message : 'Unable to load home details';
    }
  }

  /// Fetch recent security events from FastAPI endpoint
  Future<void> fetchRecentEvents(String? token) async {
    if (_currentHome == null) return;

    try {
      final responseData = await _apiClient.get(
        '/api/homes/${_currentHome!.id}/security-logs',
        token: token,
      );

      if (responseData is List) {
        final logs = responseData
            .map((item) => SecurityLogModel.fromJson(item as Map<String, dynamic>))
            .toList();

        // Sort descending by creation date
        logs.sort((a, b) => b.createdAt.compareTo(a.createdAt));
        _recentEvents = logs.take(10).toList();
      }
    } catch (e) {
      // Graceful error capture for events fetch
      if (_errorMessage == null && e is ApiException) {
        _errorMessage = e.message;
      }
    }
  }

  /// Complete initial data load (Health + Homes + Events)
  Future<void> loadHomeData(String? token) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final isOnline = await checkBackendHealth();
      if (isOnline) {
        await fetchHomes(token);
        await fetchRecentEvents(token);
      } else {
        _recentEvents = [];
      }
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Refresh action (Pull-to-refresh)
  Future<void> refresh(String? token) async {
    _isRefreshing = true;
    notifyListeners();

    try {
      final isOnline = await checkBackendHealth();
      if (isOnline) {
        await fetchHomes(token);
        await fetchRecentEvents(token);
      }
    } finally {
      _isRefreshing = false;
      notifyListeners();
    }
  }

  void setCurrentHome(HomeModel home) {
    _currentHome = home;
    notifyListeners();
  }
}
