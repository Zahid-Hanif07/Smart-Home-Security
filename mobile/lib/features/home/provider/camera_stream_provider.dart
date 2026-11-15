import 'package:flutter/foundation.dart';
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/core/network/mjpeg_stream_service.dart';

class CameraStreamProvider extends ChangeNotifier {
  final MjpegStreamService _service;
  final ApiClient _apiClient;
  String? _activeHomeId;
  String? _activeToken;
  String? _videoDiagnostic;
  String? _debugVideoStatusMessage;

  CameraStreamProvider({MjpegStreamService? service, ApiClient? apiClient})
    : _service = service ?? MjpegStreamService(),
      _apiClient = apiClient ?? ApiClient() {
    _service.statusNotifier.addListener(_onStatusChanged);
  }

  CameraStreamStatus get status => _service.status;
  ValueListenable<CameraStreamStatus> get statusNotifier =>
      _service.statusNotifier;
  MjpegStreamService get service => _service;
  Stream<Uint8List> get frames => _service.frameStream;
  String? get videoDiagnostic => _videoDiagnostic;
  String? get debugVideoStatusMessage => _debugVideoStatusMessage;

  // TEMP DEBUG: remove this read-only diagnostic after publisher verification.
  Future<void> debugCheckVideoStatus(String? homeId, String? token) async {
    if (!kDebugMode) return;

    if (homeId == null || homeId.isEmpty || token == null || token.isEmpty) {
      _debugVideoStatusMessage = 'Video status unavailable';
      notifyListeners();
      return;
    }

    try {
      final response = await _apiClient.getVideoStatus(homeId, token);
      const validReasons = {
        'no_publisher_connected',
        'publisher_home_id_mismatch',
        'no_recent_frames',
        'streaming',
      };
      if (response is! Map ||
          response['publisher_connected'] is! bool ||
          response['home_id_match'] is! bool ||
          response['reason'] is! String ||
          !validReasons.contains(response['reason'])) {
        throw const FormatException();
      }

      _debugVideoStatusMessage =
          'publisher_connected: ${response['publisher_connected']}\n'
          'home_id_match: ${response['home_id_match']}\n'
          'reason: ${response['reason']}';
    } on ApiException {
      _debugVideoStatusMessage = 'Video status unavailable';
    } catch (_) {
      _debugVideoStatusMessage = 'Video status unavailable';
    }
    notifyListeners();
  }

  Future<void> connect(
    String? homeId,
    String? token, {
    bool force = false,
  }) async {
    if (homeId == null || homeId.isEmpty || token == null || token.isEmpty) {
      _activeHomeId = null;
      _activeToken = null;
      _videoDiagnostic = null;
      _service.stopStream();
      notifyListeners();
      return;
    }
    if (!force &&
        _activeHomeId == homeId &&
        _activeToken == token &&
        status != CameraStreamStatus.idle) {
      return;
    }
    if (_activeHomeId != homeId || _activeToken != token) {
      _videoDiagnostic = null;
    }
    _activeHomeId = homeId;
    _activeToken = token;
    final url = Uri.parse(
      '${ApiConfig.baseUrl}${ApiConfig.videoStreamEndpoint}',
    ).replace(queryParameters: {'home_id': homeId}).toString();
    await _service.startStream(url, accessToken: token);
    await _refreshVideoDiagnostic(homeId, token);
  }

  Future<void> _refreshVideoDiagnostic(String homeId, String token) async {
    try {
      final response = await _apiClient.getVideoStatus(homeId, token);
      final reason = response is Map ? response['reason'] : null;
      _videoDiagnostic = switch (reason) {
        'streaming' => 'Server reports a recent camera frame',
        'no_publisher_connected' => 'Server has not received a camera frame',
        'publisher_home_id_mismatch' => 'Camera is paired with a different home',
        'no_recent_frames' => 'Camera frames are stale',
        _ => 'Camera status is unavailable',
      };
    } on ApiException catch (error) {
      _videoDiagnostic = error.statusCode == 401
          ? 'Status check unauthorized (HTTP 401)'
          : error.statusCode == null
          ? 'Status check could not reach the server'
          : 'Status check failed (HTTP ${error.statusCode})';
    } catch (_) {
      _videoDiagnostic = 'Status check could not reach the server';
    }
    notifyListeners();
  }

  Future<void> retry() => connect(_activeHomeId, _activeToken, force: true);

  Future<void> clearSessionData() => connect(null, null);

  void _onStatusChanged() => notifyListeners();

  @override
  void dispose() {
    _service.statusNotifier.removeListener(_onStatusChanged);
    _service.stopStream();
    super.dispose();
  }
}
