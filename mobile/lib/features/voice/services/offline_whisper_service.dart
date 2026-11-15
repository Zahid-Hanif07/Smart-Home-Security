import 'dart:io';

import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa_onnx;
import 'package:mobile/features/voice/services/whisper_model_manager.dart';

abstract interface class SpeechRecognitionService {
  Future<String> transcribe(String audioPath, {required String language});
}

class OfflineWhisperService implements SpeechRecognitionService {
  OfflineWhisperService({WhisperModelManager? modelManager})
    : _modelManager = modelManager ?? WhisperModelManager();

  final WhisperModelManager _modelManager;
  sherpa_onnx.OfflineRecognizer? _recognizer;
  String? _loadedLanguage;

  Future<void> _ensureInitialized(String language) async {
    if (_recognizer != null && _loadedLanguage == language) return;
    _recognizer?.free();
    _recognizer = null;
    final paths = await _modelManager.resolve();
    if (paths == null || await _modelManager.status() != WhisperModelStatus.ready) {
      throw StateError('Offline speech model is not installed.');
    }
    await sherpa_onnx.initBindingsAsync();
    final whisper = sherpa_onnx.OfflineWhisperModelConfig(
      encoder: paths.encoder,
      decoder: paths.decoder,
      language: language,
      task: 'transcribe',
    );
    final config = sherpa_onnx.OfflineRecognizerConfig(
      model: sherpa_onnx.OfflineModelConfig(
        whisper: whisper,
        tokens: paths.tokens,
        modelType: 'whisper',
        numThreads: 1,
        debug: false,
      ),
    );
    _recognizer = await sherpa_onnx.OfflineRecognizer.createAsync(config);
    _loadedLanguage = language;
  }

  @override
  Future<String> transcribe(
    String audioPath, {
    required String language,
  }) async {
    if (!audioPath.toLowerCase().endsWith('.wav')) {
      throw FormatException('Speech audio must be a PCM WAV file.');
    }
    if (!await File(audioPath).exists()) {
      throw FileSystemException('Recorded audio is unavailable.');
    }
    await _ensureInitialized(language);
    final wave = sherpa_onnx.readWave(audioPath);
    if (wave.samples.isEmpty || wave.sampleRate <= 0) {
      throw FormatException('Recorded audio is empty or unreadable.');
    }
    final stream = _recognizer!.createStream();
    try {
      stream.acceptWaveform(samples: wave.samples, sampleRate: wave.sampleRate);
      // sherpa_onnx exposes synchronous decode for an existing recognizer.
      // Model creation is asynchronous; keep this call out of widget code.
      _recognizer!.decode(stream);
      return _recognizer!.getResult(stream).text.trim();
    } finally {
      stream.free();
    }
  }

  void dispose() {
    _recognizer?.free();
    _recognizer = null;
    _loadedLanguage = null;
  }
}
