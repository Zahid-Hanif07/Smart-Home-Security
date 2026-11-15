import 'package:flutter/services.dart';

abstract interface class VoiceRecorder {
  Future<bool> start();
  Future<String?> stop();
  Future<void> cancel();
}

/// Android-only local recorder bridge. Phase 10.1 stores temporary audio only;
/// speech recognition and upload are intentionally not part of this adapter.
class AndroidAudioRecorder implements VoiceRecorder {
  static const MethodChannel _channel = MethodChannel('otto.voice/audio');

  Future<bool> start() async {
    final available = await _channel.invokeMethod<bool>('isAvailable') ?? false;
    if (!available) return false;
    return await _channel.invokeMethod<bool>('startRecording') ?? false;
  }

  Future<String?> stop() async {
    return _channel.invokeMethod<String>('stopRecording');
  }

  Future<void> cancel() async {
    await _channel.invokeMethod<void>('cancelRecording');
  }
}
