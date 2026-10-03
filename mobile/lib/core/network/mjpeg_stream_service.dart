import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

enum CameraStreamStatus {
  idle,
  connecting,
  streaming,
  error,
}

class MjpegStreamService {
  static final MjpegStreamService _instance = MjpegStreamService._internal();
  factory MjpegStreamService() => _instance;
  MjpegStreamService._internal();

  final StreamController<Uint8List> _frameController =
      StreamController<Uint8List>.broadcast();
  final ValueNotifier<CameraStreamStatus> statusNotifier =
      ValueNotifier<CameraStreamStatus>(CameraStreamStatus.idle);

  http.Client? _client;
  StreamSubscription<List<int>>? _subscription;
  String? _currentUrl;
  final List<int> _buffer = [];

  Stream<Uint8List> get frameStream => _frameController.stream;
  CameraStreamStatus get status => statusNotifier.value;
  bool get isStreaming => statusNotifier.value == CameraStreamStatus.streaming;

  /// Start or reconnect MJPEG stream from given URL
  Future<void> startStream(String streamUrl) async {
    if (statusNotifier.value == CameraStreamStatus.streaming &&
        _currentUrl == streamUrl &&
        _subscription != null) {
      return; // Already streaming target URL
    }

    stopStream();

    _currentUrl = streamUrl;
    statusNotifier.value = CameraStreamStatus.connecting;

    try {
      _client = http.Client();
      final request = http.Request('GET', Uri.parse(streamUrl));
      request.headers['Cache-Control'] = 'no-cache';
      request.headers['Pragma'] = 'no-cache';

      final response = await _client!.send(request).timeout(
        const Duration(seconds: 8),
      );

      if (response.statusCode == 200) {
        statusNotifier.value = CameraStreamStatus.streaming;
        _buffer.clear();

        _subscription = response.stream.listen(
          (chunk) {
            _handleChunk(chunk);
          },
          onError: (error) {
            _handleError('Stream connection error');
          },
          onDone: () {
            if (statusNotifier.value == CameraStreamStatus.streaming) {
              statusNotifier.value = CameraStreamStatus.idle;
            }
          },
          cancelOnError: true,
        );
      } else {
        _handleError('HTTP ${response.statusCode} Stream unavailable');
      }
    } catch (e) {
      _handleError('Unable to connect to camera stream');
    }
  }

  void _handleChunk(List<int> chunk) {
    _buffer.addAll(chunk);

    // Prevent buffer memory overflow
    if (_buffer.length > 2 * 1024 * 1024) {
      _buffer.clear();
      return;
    }

    while (_buffer.length >= 4) {
      int startIndex = -1;
      for (int i = 0; i < _buffer.length - 1; i++) {
        if (_buffer[i] == 0xFF && _buffer[i + 1] == 0xD8) {
          startIndex = i;
          break;
        }
      }

      if (startIndex == -1) {
        _buffer.clear();
        break;
      }

      int endIndex = -1;
      for (int i = startIndex + 2; i < _buffer.length - 1; i++) {
        if (_buffer[i] == 0xFF && _buffer[i + 1] == 0xD9) {
          endIndex = i;
          break;
        }
      }

      if (endIndex != -1) {
        final frameBytes = Uint8List.fromList(
          _buffer.sublist(startIndex, endIndex + 2),
        );
        _frameController.add(frameBytes);
        _buffer.removeRange(0, endIndex + 2);
      } else {
        // Incomplete frame in buffer, await next chunk
        if (startIndex > 0) {
          _buffer.removeRange(0, startIndex);
        }
        break;
      }
    }
  }

  void _handleError(String message) {
    statusNotifier.value = CameraStreamStatus.error;
    _buffer.clear();
    _subscription?.cancel();
    _subscription = null;
    _client?.close();
    _client = null;
  }

  /// Stop and cleanup streaming resources
  void stopStream() {
    _subscription?.cancel();
    _subscription = null;
    _client?.close();
    _client = null;
    _buffer.clear();
    _currentUrl = null;
    statusNotifier.value = CameraStreamStatus.idle;
  }
}
