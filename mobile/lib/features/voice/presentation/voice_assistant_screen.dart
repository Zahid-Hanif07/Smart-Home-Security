import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/features/voice/provider/voice_provider.dart';
import 'package:mobile/features/voice/services/voice_intent_parser.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

class VoiceAssistantScreen extends StatefulWidget {
  const VoiceAssistantScreen({super.key});

  @override
  State<VoiceAssistantScreen> createState() => _VoiceAssistantScreenState();
}

class _VoiceAssistantScreenState extends State<VoiceAssistantScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;
  bool _pressActive = false;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _beginPress(VoiceProvider voice) async {
    if (_pressActive || voice.isBusy) return;
    _pressActive = true;
    await voice.startRecording();
    if (!_pressActive && voice.isRecording) await voice.stopRecording();
  }

  Future<void> _endPress(VoiceProvider voice) async {
    _pressActive = false;
    if (voice.isRecording) await voice.stopRecording();
  }

  Future<void> _cancel(VoiceProvider voice) async {
    _pressActive = false;
    await voice.cancelRecording();
    if (mounted) Navigator.of(context).pop();
  }

  Future<void> _submit(VoiceProvider voice) async {
    final auth = context.read<AuthProvider>();
    final homes = context.read<HomeProvider>();
    final homeId = homes.currentHome?.id;
    final token = auth.token;
    if (homeId == null || homeId.trim().isEmpty) {
      voice.setError('Select a home before submitting a command.');
      return;
    }
    if (token == null || token.isEmpty) {
      voice.setError('Sign in again before submitting a command.');
      return;
    }
    try {
      String? roomId;
      final roomName = voice.intent?.roomName;
      if (roomName != null) {
        await homes.loadRooms(homeId, token);
        if (!mounted || homes.currentHome?.id != homeId) return;
        final matches = homes.resolveRoom(roomName);
        if (matches.isEmpty) {
          voice.setError('That room is not available in the selected home.');
          return;
        }
        if (matches.length != 1) {
          voice.setError('That room name is ambiguous in the selected home.');
          return;
        }
        roomId = matches.single.id;
      }
      final command = await voice.submitParsedIntent(
        homeId: homeId,
        token: token,
        roomId: roomId,
      );
      if (!mounted || homes.currentHome?.id != homeId) return;
      await voice.pollCommandStatus(
        homeId: homeId,
        token: token,
        commandId: command.id,
        isHomeStillSelected: () => homes.currentHome?.id == homeId,
      );
    } catch (error) {
      voice.setError(error.toString());
    }
  }

  String _status(VoiceProvider voice) {
    if (voice.errorMessage != null) return voice.errorMessage!;
    return switch (voice.state) {
      VoiceRecordingState.ready => 'Ready to listen',
      VoiceRecordingState.recording => 'Listening…',
      VoiceRecordingState.processing => 'Processing…',
      VoiceRecordingState.transcriptReady => 'Response',
      VoiceRecordingState.stopped => 'Recording stopped.',
      VoiceRecordingState.permissionDenied => 'Microphone permission denied.',
      VoiceRecordingState.microphoneUnavailable => 'Microphone unavailable.',
      VoiceRecordingState.failed => 'Speech recognition failed.',
    };
  }

  String _helper(VoiceProvider voice) {
    if (voice.transcript != null) {
      return voice.intent?.message ?? 'Transcript received.';
    }
    if (voice.state == VoiceRecordingState.processing) {
      return 'Understanding your request locally.';
    }
    return 'Press and hold the microphone to speak. Your audio stays on this device.';
  }

  @override
  Widget build(BuildContext context) {
    final voice = context.watch<VoiceProvider>();
    final listening = voice.isRecording;
    final canRetry =
        voice.state == VoiceRecordingState.failed ||
        voice.state == VoiceRecordingState.transcriptReady ||
        voice.state == VoiceRecordingState.stopped;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          child: Column(
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => _cancel(voice),
                  child: const Text('Cancel'),
                ),
              ),
              const Spacer(),
              Text(
                _status(voice),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 10),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 310),
                child: Text(
                  _helper(voice),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 14,
                    height: 1.4,
                  ),
                ),
              ),
              if (voice.transcript != null) ...[
                const SizedBox(height: 24),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Text(
                    voice.transcript!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 15,
                    ),
                  ),
                ),
                if ({
                  VoiceIntentType.lightOn,
                  VoiceIntentType.lightOff,
                  VoiceIntentType.allLightsOn,
                  VoiceIntentType.allLightsOff,
                }.contains(voice.intent?.type)) ...[
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: voice.isBusy ? null : () => _submit(voice),
                    child: const Text('Submit command'),
                  ),
                ],
              ],
              if (voice.lastCommand != null) ...[
                const SizedBox(height: 12),
                Text('Backend status: ${voice.lastCommand!.status}'),
              ],
              const Spacer(),
              AnimatedBuilder(
                animation: _pulse,
                builder: (context, child) {
                  final active =
                      listening ||
                      voice.state == VoiceRecordingState.processing;
                  final scale = active ? 1 + (_pulse.value * .06) : 1.0;
                  return Transform.scale(scale: scale, child: child);
                },
                child: GestureDetector(
                  onTapDown: (_) => unawaited(_beginPress(voice)),
                  onTapUp: (_) => unawaited(_endPress(voice)),
                  onTapCancel: () => unawaited(_endPress(voice)),
                  child: Semantics(
                    button: true,
                    label: 'Press and hold to speak',
                    child: Container(
                      width: 116,
                      height: 116,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.champagne,
                        boxShadow: [
                          BoxShadow(
                            color:
                                (listening
                                        ? AppColors.forest
                                        : AppColors.champagne)
                                    .withValues(alpha: listening ? .32 : .22),
                            blurRadius: listening ? 30 : 18,
                            spreadRadius: listening ? 8 : 3,
                          ),
                        ],
                      ),
                      child: Icon(
                        listening ? Icons.mic_rounded : Icons.mic_none_rounded,
                        color: AppColors.emeraldInk,
                        size: 42,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Text(
                listening ? 'Release to process' : 'Press and hold to speak',
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
              ),
              if (canRetry) ...[
                const SizedBox(height: 14),
                TextButton.icon(
                  onPressed: voice.isBusy ? null : voice.cancelRecording,
                  icon: const Icon(Icons.refresh_rounded, size: 17),
                  label: const Text('Try again'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
