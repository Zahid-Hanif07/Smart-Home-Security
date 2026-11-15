import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/voice/services/android_audio_recorder.dart';
import 'package:mobile/features/voice/services/offline_whisper_service.dart';
import 'package:mobile/features/voice/services/voice_intent_parser.dart';
import 'package:mobile/models/voice_command_model.dart';

enum VoiceRecordingState {
  ready,
  recording,
  processing,
  transcriptReady,
  stopped,
  permissionDenied,
  microphoneUnavailable,
  failed,
}

class VoiceProvider extends ChangeNotifier {
  final VoiceRecorder _recorder;
  final SpeechRecognitionService? _recognizer;
  final ApiClient? _apiClient;
  final VoiceIntentParser _intentParser = const VoiceIntentParser();
  VoiceRecordingState _state = VoiceRecordingState.ready;
  String? _lastRecordingPath;
  String? _errorMessage;
  String? _transcript;
  VoiceIntent? _intent;
  String _language;
  VoiceCommandModel? _lastCommand;
  VoiceCommandSubmission? _lastSubmission;
  String? _pendingCommandId;
  String? _pendingHomeId;
  int _pollGeneration = 0;
  bool _disposed = false;

  VoiceProvider({
    VoiceRecorder? recorder,
    SpeechRecognitionService? recognizer,
    ApiClient? apiClient,
    String language = 'ur',
  }) : _language = language,
       _recorder = recorder ?? AndroidAudioRecorder(),
       _recognizer = recognizer,
       _apiClient = apiClient;

  VoiceRecordingState get state => _state;
  String? get errorMessage => _errorMessage;
  String? get transcript => _transcript;
  VoiceIntent? get intent => _intent;
  String get language => _language;
  bool get isRecording => _state == VoiceRecordingState.recording;
  bool get isBusy => isRecording || _state == VoiceRecordingState.processing;
  VoiceCommandModel? get lastCommand => _lastCommand;
  VoiceCommandSubmission? get lastSubmission => _lastSubmission;
  String? get backendStatus => _lastCommand?.status;

  void setError(String message) {
    _errorMessage = message;
    if (!_disposed) notifyListeners();
  }

  Future<VoiceCommandModel> submitParsedIntent({
    required String homeId,
    required String token,
    String? roomId,
  }) async {
    final parsed = _intent;
    final api = _apiClient;
    if (parsed == null || api == null) {
      throw StateError('No parsed command is available.');
    }
    final command = switch (parsed.type) {
      VoiceIntentType.lightOn => 'light_on',
      VoiceIntentType.lightOff => 'light_off',
      VoiceIntentType.allLightsOn => 'all_lights_on',
      VoiceIntentType.allLightsOff => 'all_lights_off',
      _ => throw StateError('This voice intent is not executable.'),
    };
    final allLights = command.startsWith('all_');
    if (!allLights && (roomId == null || roomId.trim().isEmpty)) {
      throw StateError('A verified room is required.');
    }
    final cleanHomeId = homeId.trim();
    final commandId =
        (_pendingHomeId == cleanHomeId && _pendingCommandId != null)
        ? _pendingCommandId!
        : _newCommandId();
    _pendingHomeId = cleanHomeId;
    _pendingCommandId = commandId;
    final submitted = await api.createVoiceCommand(
      cleanHomeId,
      commandId,
      command,
      allLights ? 'all_lights' : 'room',
      allLights ? null : roomId!.trim(),
      token,
    );
    if (_disposed) return submitted.command;
    _lastSubmission = submitted;
    _lastCommand = submitted.command;
    notifyListeners();
    return submitted.command;
  }

  Future<void> pollCommandStatus({
    required String homeId,
    required String token,
    required String commandId,
    bool Function()? isHomeStillSelected,
    Duration interval = const Duration(seconds: 1),
    int maxAttempts = 15,
  }) async {
    final generation = ++_pollGeneration;
    for (var attempt = 0; attempt < maxAttempts; attempt++) {
      if (_disposed || generation != _pollGeneration) return;
      if (isHomeStillSelected != null && !isHomeStillSelected()) return;
      if (attempt > 0) await Future<void>.delayed(interval);
      final command = await _apiClient?.getVoiceCommand(
        homeId,
        commandId,
        token,
      );
      if (command == null || _disposed || generation != _pollGeneration) return;
      if (isHomeStillSelected != null && !isHomeStillSelected()) return;
      _lastCommand = command;
      notifyListeners();
      if (_isTerminal(command.status)) return;
    }
  }

  bool _isTerminal(String status) => {
    'acknowledged',
    'partially_acknowledged',
    'failed',
    'timed_out',
    'unknown_outcome',
    'rejected',
    'expired',
  }.contains(status);

  String _newCommandId() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }

  void setLanguage(String language) {
    if (language != 'ur' && language != 'en') return;
    _language = language;
    notifyListeners();
  }

  Future<void> startRecording() async {
    if (isRecording) return;
    await _discardLastRecording();
    _pendingCommandId = null;
    _pendingHomeId = null;
    _errorMessage = null;
    _transcript = null;
    _intent = null;
    try {
      final started = await _recorder.start();
      if (started) {
        _setState(VoiceRecordingState.recording);
      } else {
        _setState(VoiceRecordingState.microphoneUnavailable);
        _errorMessage = 'Microphone unavailable.';
      }
    } on PlatformException catch (error) {
      if (error.code == 'permission_denied') {
        _setState(VoiceRecordingState.permissionDenied);
        _errorMessage = 'Microphone permission is required.';
      } else {
        _setState(VoiceRecordingState.failed);
        _errorMessage = 'Recording could not be started.';
      }
    } catch (_) {
      _setState(VoiceRecordingState.failed);
      _errorMessage = 'Recording could not be started.';
    }
    notifyListeners();
  }

  Future<void> stopRecording() async {
    if (!isRecording) return;
    try {
      _lastRecordingPath = await _recorder.stop();
      if (_lastRecordingPath == null) {
        _setState(VoiceRecordingState.failed);
        _errorMessage = 'Recording could not be saved temporarily.';
      } else {
        if (_recognizer == null) {
          _setState(VoiceRecordingState.stopped);
        } else {
          _setState(VoiceRecordingState.processing);
          notifyListeners();
          try {
            _transcript = await _recognizer.transcribe(
              _lastRecordingPath!,
              language: _language,
            );
            if (_transcript!.isEmpty) {
              _setState(VoiceRecordingState.failed);
              _errorMessage = 'No speech was recognized.';
            } else {
              _intent = _intentParser.parse(_transcript!);
              _setState(VoiceRecordingState.transcriptReady);
            }
          } on StateError catch (error) {
            _setState(VoiceRecordingState.failed);
            _errorMessage = error.message;
          } on FormatException catch (error) {
            _setState(VoiceRecordingState.failed);
            _errorMessage = error.message;
          } catch (_) {
            _setState(VoiceRecordingState.failed);
            _errorMessage = 'Speech recognition failed.';
          }
        }
      }
    } catch (_) {
      _setState(VoiceRecordingState.failed);
      _errorMessage = 'Recording could not be stopped safely.';
    }
    notifyListeners();
  }

  Future<void> cancelRecording() async {
    _pollGeneration++;
    _pendingCommandId = null;
    _pendingHomeId = null;
    try {
      await _recorder.cancel();
    } catch (_) {
      // Cleanup remains best-effort and must not surface platform details.
    }
    _lastRecordingPath = null;
    _transcript = null;
    _intent = null;
    _errorMessage = null;
    _setState(VoiceRecordingState.ready);
    notifyListeners();
  }

  Future<void> _discardLastRecording() async {
    if (_lastRecordingPath == null) return;
    try {
      await _recorder.cancel();
    } catch (_) {}
    _lastRecordingPath = null;
  }

  void _setState(VoiceRecordingState value) {
    _state = value;
  }

  @override
  void dispose() {
    _disposed = true;
    _pollGeneration++;
    unawaited(_recorder.cancel());
    if (_recognizer case final OfflineWhisperService recognizer) {
      recognizer.dispose();
    }
    super.dispose();
  }
}
