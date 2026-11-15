import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/voice/provider/voice_provider.dart';
import 'package:mobile/features/voice/services/android_audio_recorder.dart';

class FakeVoiceRecorder implements VoiceRecorder {
  bool available = true;
  bool failStart = false;
  bool failStop = false;
  bool started = false;
  int startCalls = 0;
  int stopCalls = 0;
  int cancelCalls = 0;

  @override
  Future<bool> start() async {
    startCalls++;
    if (failStart) throw PlatformException(code: 'permission_denied');
    if (!available) return false;
    started = true;
    return true;
  }

  @override
  Future<String?> stop() async {
    stopCalls++;
    if (failStop) throw StateError('stop failed');
    started = false;
    return '/cache/otto_voice_test.m4a';
  }

  @override
  Future<void> cancel() async {
    cancelCalls++;
    started = false;
  }
}

void main() {
  test('does not record automatically', () {
    final recorder = FakeVoiceRecorder();
    final provider = VoiceProvider(recorder: recorder);
    expect(provider.state, VoiceRecordingState.ready);
    expect(recorder.startCalls, 0);
    provider.dispose();
  });

  test('starts and stops with permission granted', () async {
    final recorder = FakeVoiceRecorder();
    final provider = VoiceProvider(recorder: recorder);

    await provider.startRecording();
    expect(provider.state, VoiceRecordingState.recording);
    await provider.stopRecording();
    expect(provider.state, VoiceRecordingState.stopped);
    expect(recorder.stopCalls, 1);
    provider.dispose();
  });

  test('permission denial is safe', () async {
    final recorder = FakeVoiceRecorder()..failStart = true;
    final provider = VoiceProvider(recorder: recorder);

    await provider.startRecording();

    expect(provider.state, VoiceRecordingState.permissionDenied);
    expect(provider.errorMessage, isNotNull);
    provider.dispose();
  });

  test('unavailable microphone is safe', () async {
    final recorder = FakeVoiceRecorder()..available = false;
    final provider = VoiceProvider(recorder: recorder);

    await provider.startRecording();

    expect(provider.state, VoiceRecordingState.microphoneUnavailable);
    provider.dispose();
  });

  test('cancel releases active recording', () async {
    final recorder = FakeVoiceRecorder();
    final provider = VoiceProvider(recorder: recorder);

    await provider.startRecording();
    await provider.cancelRecording();

    expect(provider.state, VoiceRecordingState.ready);
    expect(recorder.cancelCalls, 1);
    provider.dispose();
  });

  test('stop failure does not leave recording state active', () async {
    final recorder = FakeVoiceRecorder()..failStop = true;
    final provider = VoiceProvider(recorder: recorder);

    await provider.startRecording();
    await provider.stopRecording();

    expect(provider.state, VoiceRecordingState.failed);
    expect(provider.isRecording, isFalse);
    provider.dispose();
  });
}
