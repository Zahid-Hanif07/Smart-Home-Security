import 'dart:async';

import 'package:flutter/material.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/models/home_model.dart';
import 'package:mobile/models/pairing_code_model.dart';
import 'package:mobile/models/security_log_model.dart';
import 'package:mobile/models/room_model.dart';
import 'package:mobile/core/storage/local_storage.dart';

enum SecurityStatusState { secure, alert, unknownActivity, offline }

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
  List<RoomModel> _rooms = [];
  String? _roomsHomeId;
  bool _roomsLoading = false;

  final addHomeFormKey = GlobalKey<FormState>();
  final addHomeNameController = TextEditingController();
  final addHomeAddressController = TextEditingController();
  bool _homeManagementLoaded = false;
  bool dashboardLoadStarted = false;
  Timer? _eventsRealtimeTimer;
  String? _realtimeHomeId;
  String? _realtimeToken;
  bool _eventsRefreshInFlight = false;

  Future<void> initializeDashboard(String? token) async {
    if (dashboardLoadStarted || (_isBackendConnected && !_isCheckingBackend)) {
      return;
    }
    dashboardLoadStarted = true;
    await loadHomeData(token);
  }

  Future<void> initializeHomeManagement(String? token) async {
    if (_homeManagementLoaded) return;
    // Set this before notifying so screen rebuilds do not start duplicate
    // requests. Failures remain retryable through retryInitialHomeSetup.
    _homeManagementLoaded = true;
    if (token != null && token.isNotEmpty) {
      await setupHomesForAuthenticatedUser(token);
    } else {
      await fetchHomes(token);
    }
  }

  /// Verify the authenticated profile, then load homes and ensure one exists.
  /// The backend endpoint is idempotent and only called after an empty list.
  Future<bool> setupHomesForAuthenticatedUser(String? token) async {
    if (token == null || token.isEmpty) {
      _errorMessage = 'Sign in again to finish setting up your home.';
      notifyListeners();
      return false;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await _apiClient.get('/api/auth/me', token: token);
      await _loadHomes(token);
      if (_homes.isEmpty) {
        final created = await _apiClient.post(
          '/api/homes/initial',
          token: token,
        );
        if (created is! Map<String, dynamic>) {
          throw ApiException(
            message: 'The server returned an invalid initial home response.',
          );
        }
        final home = HomeModel.fromJson(created);
        _homes = [home];
        _currentHome = home;
        await LocalStorage.saveSelectedHomeId(home.id);
      }
      _homeManagementLoaded = true;
      dashboardLoadStarted = true;
      return true;
    } catch (e) {
      _errorMessage = e is ApiException
          ? e.message
          : 'Home setup failed: ${e.toString()}';
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> retryInitialHomeSetup(String? token) =>
      setupHomesForAuthenticatedUser(token);

  /// Keep dashboard events fresh using the authenticated API, without requiring
  /// Supabase Realtime publication settings to be enabled on the project.
  void startRealtimeUpdates(String? homeId, String? token) {
    if (homeId == null || homeId.isEmpty || token == null || token.isEmpty) {
      stopRealtimeUpdates();
      return;
    }
    if (_eventsRealtimeTimer != null &&
        _realtimeHomeId == homeId &&
        _realtimeToken == token) {
      return;
    }
    stopRealtimeUpdates();
    _realtimeHomeId = homeId;
    _realtimeToken = token;
    _eventsRealtimeTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!_eventsRefreshInFlight && _currentHome?.id == homeId) {
        _eventsRefreshInFlight = true;
        _refreshRealtimeState(homeId, token).whenComplete(() {
          _eventsRefreshInFlight = false;
        });
      }
    });
  }

  Future<void> _refreshRealtimeState(String homeId, String token) async {
    final online = await _apiClient.checkHealth();
    if (_currentHome?.id != homeId) return;
    _isBackendConnected = online;
    if (online) {
      await fetchRecentEvents(token);
    } else {
      _recentEvents = [];
      notifyListeners();
    }
  }

  void stopRealtimeUpdates() {
    _eventsRealtimeTimer?.cancel();
    _eventsRealtimeTimer = null;
    _realtimeHomeId = null;
    _realtimeToken = null;
  }

  HomeProvider({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  List<HomeModel> get homes => List.unmodifiable(_homes);
  HomeModel? get currentHome => _currentHome;
  List<SecurityLogModel> get recentEvents => List.unmodifiable(_recentEvents);
  bool get isBackendConnected => _isBackendConnected;
  bool get isCheckingBackend => _isCheckingBackend;
  bool get isLoading => _isLoading;
  bool get isRefreshing => _isRefreshing;
  String? get errorMessage => _errorMessage;
  List<RoomModel> get rooms => List.unmodifiable(_rooms);
  bool get roomsLoading => _roomsLoading;

  Future<List<RoomModel>> loadRooms(String homeId, String? token) async {
    final cleanHomeId = homeId.trim();
    if (_roomsHomeId == cleanHomeId) return rooms;
    _roomsLoading = true;
    notifyListeners();
    try {
      final loaded = await _apiClient.getHomeRooms(cleanHomeId, token);
      if (_currentHome?.id != cleanHomeId) return const [];
      _rooms = loaded;
      _roomsHomeId = cleanHomeId;
      return rooms;
    } finally {
      _roomsLoading = false;
      notifyListeners();
    }
  }

  List<RoomModel> resolveRoom(String name) {
    final normalized = name.trim().toLowerCase().replaceAll(
      RegExp(r'\s+'),
      ' ',
    );
    return _rooms.where((room) => room.normalizedName == normalized).toList();
  }

  SecurityStatusState get securityStatus {
    if (!_isBackendConnected) {
      return SecurityStatusState.offline;
    }
    if (_recentEvents.any(
      (e) =>
          e.eventType.toLowerCase() == 'unknown_person' ||
          e.isAuthorized == false,
    )) {
      return SecurityStatusState.alert;
    }
    if (_recentEvents.any(
      (e) => e.eventType.toLowerCase() == 'motion_detected',
    )) {
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

  /// Fetch only. Empty lists remain empty; setup is an explicit idempotent flow.
  Future<void> fetchHomes(String? token) async {
    _errorMessage = null;

    try {
      await _loadHomes(token);
    } catch (e) {
      _errorMessage = e is ApiException
          ? e.message
          : 'Unable to load home details';
    } finally {
      notifyListeners();
    }
  }

  Future<void> _loadHomes(String? token) async {
    final responseData = await _apiClient.get('/api/homes', token: token);
    if (responseData is! List) {
      throw ApiException(
        message: 'The server returned an invalid homes response.',
      );
    }
    final fetched = responseData
        .map((item) => HomeModel.fromJson(item as Map<String, dynamic>))
        .toList();
    final savedId = await LocalStorage.restoreSelectedHomeId();
    final previousId = _currentHome?.id;
    _homes = fetched;
    final preferredId = savedId ?? previousId;
    _currentHome = null;
    for (final home in fetched) {
      if (home.id == preferredId) {
        _currentHome = home;
        break;
      }
    }
    _currentHome ??= fetched.isNotEmpty ? fetched.first : null;
    if (_currentHome != null) {
      await LocalStorage.saveSelectedHomeId(_currentHome!.id);
    } else {
      await LocalStorage.clearSelectedHomeId();
    }
  }

  /// Fetch recent security events from FastAPI endpoint
  Future<void> fetchRecentEvents(String? token) async {
    if (_currentHome == null) return;
    final requestedHomeId = _currentHome!.id;

    try {
      final responseData = await _apiClient.get(
        '/api/homes/${_currentHome!.id}/security-logs',
        token: token,
      );

      if (responseData is List) {
        final logs = responseData
            .map(
              (item) => SecurityLogModel.fromJson(item as Map<String, dynamic>),
            )
            .toList();

        // Sort descending by creation date
        logs.sort((a, b) => b.createdAt.compareTo(a.createdAt));
        if (_currentHome?.id == requestedHomeId) {
          _recentEvents = logs.take(10).toList();
        }
      }
    } catch (e) {
      // Graceful error capture for events fetch
      if (_errorMessage == null && e is ApiException) {
        _errorMessage = e.message;
      }
    } finally {
      notifyListeners();
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
        if (token != null && token.isNotEmpty) {
          await setupHomesForAuthenticatedUser(token);
        } else {
          await fetchHomes(token);
        }
        await fetchRecentEvents(token);
      } else {
        _recentEvents = [];
        if (token != null && token.isNotEmpty) {
          _errorMessage =
              'Backend unavailable. Home setup was not confirmed; retry when the connection returns.';
        }
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
    if (_roomsHomeId != home.id) {
      _rooms = [];
      _roomsHomeId = null;
    }
    notifyListeners();
  }

  void clearSessionData() {
    stopRealtimeUpdates();
    _homes = [];
    _currentHome = null;
    _rooms = [];
    _roomsHomeId = null;
    _recentEvents = [];
    _errorMessage = null;
    dashboardLoadStarted = false;
    _homeManagementLoaded = false;
    _isBackendConnected = false;
    LocalStorage.clearSelectedHomeId();
    notifyListeners();
  }

  /// Create a new home via POST /api/homes
  Future<HomeModel?> createHome(
    String? token,
    String name,
    String? address,
  ) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final body = {'name': name.trim(), 'address': address?.trim()};
      final res = await _apiClient.post('/api/homes', body: body, token: token);
      if (res is Map<String, dynamic>) {
        final newHome = HomeModel.fromJson(res);
        _homes.add(newHome);
        _currentHome = newHome;
        _rooms = [];
        _roomsHomeId = null;
        await LocalStorage.saveSelectedHomeId(newHome.id);
        addHomeNameController.clear();
        addHomeAddressController.clear();
        addHomeFormKey.currentState?.reset();
        _isLoading = false;
        notifyListeners();
        return newHome;
      }
      throw ApiException(message: 'Invalid response creating home.');
    } catch (e) {
      _isLoading = false;
      _errorMessage = e is ApiException
          ? e.message
          : 'Failed to create home: ${e.toString()}';
      notifyListeners();
      return null;
    }
  }

  /// Select active home and refresh events
  Future<void> selectHome(HomeModel home, String? token) async {
    if (!_homes.any((candidate) => candidate.id == home.id)) {
      _errorMessage = 'This home is not in your verified homes list.';
      notifyListeners();
      return;
    }
    _currentHome = home;
    if (_roomsHomeId != home.id) {
      _rooms = [];
      _roomsHomeId = null;
    }
    await LocalStorage.saveSelectedHomeId(home.id);
    notifyListeners();
    if (_isBackendConnected) {
      await fetchRecentEvents(token);
    }
  }

  /// Generate a short-lived pairing code for a verified owner home.
  Future<PairingCode> generatePairingCode(String? token, String homeId) async {
    final cleanHomeId = homeId.trim();
    if (token == null || token.isEmpty) {
      throw ApiException(message: 'Sign in again to pair a camera.');
    }
    if (cleanHomeId.isEmpty || !_homes.any((home) => home.id == cleanHomeId)) {
      throw ApiException(message: 'Select one of your verified homes first.');
    }

    final response = await _apiClient.post(
      '/api/homes/$cleanHomeId/pairing-codes',
      token: token,
    );
    if (response is! Map<String, dynamic>) {
      throw ApiException(
        message: 'The server returned an invalid pairing code response.',
      );
    }

    final pairingCode = PairingCode.fromJson(response);
    if (pairingCode.homeId != cleanHomeId) {
      throw ApiException(
        message: 'The server returned a pairing code for a different home.',
      );
    }
    return pairingCode;
  }

  Future<HomeModel?> updateHome(
    String? token,
    String homeId,
    String name,
    String? address,
  ) async {
    if (homeId.trim().isEmpty || !_homes.any((home) => home.id == homeId)) {
      _errorMessage = 'Select one of your homes before editing it.';
      notifyListeners();
      return null;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      final result = await _apiClient.put(
        '/api/homes/$homeId',
        token: token,
        body: {'name': name.trim(), 'address': address?.trim()},
      );
      if (result is! Map<String, dynamic>) {
        throw ApiException(
          message: 'The server returned an invalid home response.',
        );
      }
      final updated = HomeModel.fromJson(result);
      final index = _homes.indexWhere((home) => home.id == homeId);
      _homes[index] = updated;
      if (_currentHome?.id == homeId) _currentHome = updated;
      return updated;
    } catch (e) {
      _errorMessage = e is ApiException
          ? e.message
          : 'Failed to update home: $e';
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    stopRealtimeUpdates();
    addHomeNameController.dispose();
    addHomeAddressController.dispose();
    super.dispose();
  }
}
