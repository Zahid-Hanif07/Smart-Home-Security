import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/models/face_occlusion_diagnostic_model.dart';

enum FaceOcclusionViewState {
  idle,
  loading,
  waiting,
  analyzed,
  uncertain,
  unavailable,
  failed,
  stale,
  noFace,
  error,
}

class FaceOcclusionProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  final Duration pollingInterval;
  Timer? _timer;
  String? _activeHomeId;
  String? _activeToken;
  int _generation = 0;
  bool _requestInFlight = false;
  List<FaceOcclusionDiagnostic> _results = const [];
  FaceOcclusionViewState _state = FaceOcclusionViewState.idle;
  String? _errorMessage;

  FaceOcclusionProvider({
    ApiClient? apiClient,
    this.pollingInterval = const Duration(seconds: 5),
  }) : _apiClient = apiClient ?? ApiClient();

  List<FaceOcclusionDiagnostic> get results => List.unmodifiable(_results);
  FaceOcclusionViewState get state => _state;
  String? get errorMessage => _errorMessage;

  void startPolling(String? homeId, String? token) {
    if (homeId == null || homeId.isEmpty || token == null || token.isEmpty) {
      stopPolling(clear: true);
      return;
    }
    if (_activeHomeId == homeId &&
        _activeToken == token &&
        _timer != null) {
      return;
    }

    _timer?.cancel();
    _timer = null;
    _generation++;
    _activeHomeId = homeId;
    _activeToken = token;
    _results = const [];
    _errorMessage = null;
    _state = FaceOcclusionViewState.loading;
    notifyListeners();
    _fetch(_generation, homeId, token);
    _timer = Timer.periodic(pollingInterval, (_) {
      _fetch(_generation, homeId, token);
    });
  }

  void stopPolling({bool clear = false}) {
    _timer?.cancel();
    _timer = null;
    _generation++;
    _activeHomeId = null;
    _activeToken = null;
    if (clear) {
      _results = const [];
      _errorMessage = null;
      _state = FaceOcclusionViewState.idle;
      notifyListeners();
    }
  }

  Future<void> refresh(String? homeId, String? token) async {
    if (homeId == null || homeId.isEmpty || token == null || token.isEmpty) {
      stopPolling(clear: true);
      return;
    }
    if (_activeHomeId != homeId || _activeToken != token) {
      startPolling(homeId, token);
      return;
    }
    await _fetch(_generation, homeId, token);
  }

  Future<void> _fetch(int generation, String homeId, String token) async {
    if (_requestInFlight || generation != _generation) return;
    _requestInFlight = true;
    try {
      final response = await _apiClient.getFaceOcclusionStatus(homeId, token);
      if (generation != _generation ||
          _activeHomeId != homeId ||
          _activeToken != token) {
        return;
      }
      if (response is! Map<String, dynamic>) {
        throw ApiException(message: 'Invalid FaceOcc status response.');
      }
      final parsed = FaceOcclusionStatusResponse.fromJson(response);
      if (parsed.homeId != homeId) {
        _results = const [];
        _errorMessage = 'Face analysis is unavailable.';
        _state = FaceOcclusionViewState.error;
        return;
      }
      _results = parsed.results;
      _errorMessage = null;
      _state = _stateFor(parsed.results);
    } on ApiException catch (error) {
      if (generation == _generation) {
        _errorMessage = _safeError(error);
        _state = FaceOcclusionViewState.error;
      }
    } catch (_) {
      if (generation == _generation) {
        _errorMessage = 'Face analysis is unavailable.';
        _state = FaceOcclusionViewState.error;
      }
    } finally {
      _requestInFlight = false;
      if (generation == _generation) notifyListeners();
    }
  }

  static FaceOcclusionViewState _stateFor(
    List<FaceOcclusionDiagnostic> results,
  ) {
    const knownStatuses = {
      'success',
      'unavailable',
      'invalid',
      'failed',
      'no_face',
      'stale',
    };
    if (results.isEmpty) return FaceOcclusionViewState.waiting;
    if (results.any((item) => item.isStale)) return FaceOcclusionViewState.stale;
    if (results.any((item) => !knownStatuses.contains(item.status))) {
      return FaceOcclusionViewState.uncertain;
    }
    if (results.any((item) => item.status == 'no_face')) {
      return FaceOcclusionViewState.noFace;
    }
    if (results.any((item) => item.status == 'unavailable')) {
      return FaceOcclusionViewState.unavailable;
    }
    if (results.any((item) => item.status == 'failed')) {
      return FaceOcclusionViewState.failed;
    }
    if (results.any((item) => item.status == 'invalid' || item.status == 'unknown')) {
      return FaceOcclusionViewState.uncertain;
    }
    return FaceOcclusionViewState.analyzed;
  }

  static String _safeError(ApiException error) {
    switch (error.statusCode) {
      case 401:
        return 'Face analysis requires sign-in.';
      case 403:
      case 404:
      case 422:
        return 'Face analysis is not available for this home.';
      default:
        return error.statusCode == null
            ? 'Face analysis could not reach the server.'
            : 'Face analysis is temporarily unavailable.';
    }
  }

  @override
  void dispose() {
    stopPolling();
    super.dispose();
  }
}
