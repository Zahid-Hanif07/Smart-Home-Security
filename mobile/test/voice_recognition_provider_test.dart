import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/voice/services/voice_intent_parser.dart';
import 'package:mobile/features/voice/provider/voice_provider.dart';
import 'package:mobile/features/voice/services/android_audio_recorder.dart';
import 'package:mobile/features/voice/services/offline_whisper_service.dart';

class _Recorder implements VoiceRecorder {
  @override
  Future<bool> start() async => true;

  @override
  Future<String?> stop() async => '/cache/voice.wav';

  @override
  Future<void> cancel() async {}
}

class _Recognizer implements SpeechRecognitionService {
  String? language;

  @override
  Future<String> transcribe(String path, {required String language}) async {
    this.language = language;
    return 'show security status';
  }
}

void main() {
  test('transcribes a stopped recording and parses its safe intent', () async {
    final recognizer = _Recognizer();
    final provider = VoiceProvider(
      recorder: _Recorder(),
      recognizer: recognizer,
    );

    await provider.startRecording();
    await provider.stopRecording();

    expect(provider.state, VoiceRecordingState.transcriptReady);
    expect(provider.transcript, 'show security status');
    expect(provider.intent?.type, VoiceIntentType.securityStatus);
    expect(recognizer.language, 'ur');
    provider.dispose();
  });
}
