import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/models/alert_model.dart';

class AlertsProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  List<AlertModel> _alerts = const [];
  bool _isLoading = false;
  String? _error;
  String? _loadedHomeId;
  bool _hasLoaded = false;
  String? _requestedHomeId;
  DateTime? _lastAttemptAt;
  Timer? _realtimeTimer;
  String? _realtimeHomeId;
  String? _realtimeToken;

  AlertsProvider({ApiClient? apiClient})
    : _apiClient = apiClient ?? ApiClient();

  List<AlertModel> get alerts => List.unmodifiable(_alerts);
  bool get isLoading => _isLoading;
  String? get error => _error;
  int get unreadCount => _alerts.where((alert) => !alert.isRead).length;

  /// Poll the owner-authorized alerts API so new alerts appear while the
  /// dashboard remains open even when Supabase Realtime is not configured.
  void startRealtimeUpdates(String? homeId, String? token) {
    if (homeId == null || homeId.isEmpty || token == null || token.isEmpty) {
      stopRealtimeUpdates();
      return;
    }
    if (_realtimeTimer != null &&
        _realtimeHomeId == homeId &&
        _realtimeToken == token) {
      return;
    }
    stopRealtimeUpdates();
    _realtimeHomeId = homeId;
    _realtimeToken = token;
    _realtimeTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!_isLoading) load(homeId, token, force: true);
    });
  }

  void stopRealtimeUpdates() {
    _realtimeTimer?.cancel();
    _realtimeTimer = null;
    _realtimeHomeId = null;
    _realtimeToken = null;
  }

  void clearSessionData() {
    stopRealtimeUpdates();
    _alerts = const [];
    _error = null;
    _loadedHomeId = null;
    _hasLoaded = false;
    _requestedHomeId = null;
    _lastAttemptAt = null;
    notifyListeners();
  }

  Future<void> load(String? homeId, String? token, {bool force = false}) async {
    if (homeId == null || homeId.isEmpty || token == null || token.isEmpty) {
      _alerts = const [];
      _error = 'Select a home and sign in to view alerts.';
      notifyListeners();
      return;
    }
    if (!force && _hasLoaded && _loadedHomeId == homeId) return;
    if (!force && _isLoading && _requestedHomeId == homeId) return;
    if (!force &&
        _requestedHomeId == homeId &&
        _lastAttemptAt != null &&
        DateTime.now().difference(_lastAttemptAt!) <
            const Duration(seconds: 10)) {
      return;
    }
    if (_isLoading) return;
    _isLoading = true;
    _requestedHomeId = homeId;
    _lastAttemptAt = DateTime.now();
    _error = null;
    notifyListeners();
    try {
      final result = await _apiClient.get(
        '/api/homes/$homeId/alerts',
        token: token,
      );
      if (result is! List) {
        throw ApiException(message: 'Invalid alerts response.');
      }
      _alerts =
          result
              .whereType<Map<String, dynamic>>()
              .map(AlertModel.fromJson)
              .toList()
            ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      _loadedHomeId = homeId;
      _hasLoaded = true;
    } catch (e) {
      _error = e is ApiException
          ? e.message
          : 'Unable to load security alerts.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> markRead(String alertId, bool isRead, String? token) async {
    if (alertId.isEmpty || token == null || token.isEmpty) return false;
    try {
      await _apiClient.put(
        '/api/alerts/$alertId/read',
        body: {'is_read': isRead},
        token: token,
      );
      _alerts = _alerts
          .map(
            (item) => item.id == alertId
                ? AlertModel(
                    id: item.id,
                    homeId: item.homeId,
                    type: item.type,
                    title: item.title,
                    message: item.message,
                    imagePath: item.imagePath,
                    isRead: isRead,
                    createdAt: item.createdAt,
                  )
                : item,
          )
          .toList();
      notifyListeners();
      return true;
    } catch (e) {
      _error = e is ApiException ? e.message : 'Unable to update alert.';
      notifyListeners();
      return false;
    }
  }

  @override
  void dispose() {
    stopRealtimeUpdates();
    super.dispose();
  }
}
