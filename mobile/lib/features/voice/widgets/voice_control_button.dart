import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/features/voice/provider/voice_provider.dart';

class VoiceControlButton extends StatelessWidget {
  const VoiceControlButton({super.key});

  @override
  Widget build(BuildContext context) {
    final voice = context.watch<VoiceProvider>();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 16),
      decoration: BoxDecoration(
        color: AppColors.emeraldInk,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Voice control',
            style: TextStyle(
              color: AppColors.white,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Push to talk. Speech is processed locally when the model is installed.',
            style: TextStyle(color: Color(0xFFD1DFD8), fontSize: 12),
          ),
          const SizedBox(height: 18),
          Center(
            child: Semantics(
              button: true,
              label: 'Open voice assistant',
              child: InkWell(
                onTap: () => Navigator.of(context).pushNamed(
                  AppRoutes.voiceAssistant,
                ),
                borderRadius: BorderRadius.circular(40),
                child: Ink(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 34,
                    vertical: 15,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.champagne,
                    borderRadius: BorderRadius.circular(40),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.champagne.withValues(alpha: .16),
                        blurRadius: 18,
                        spreadRadius: 3,
                      ),
                    ],
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.mic_none_rounded, color: AppColors.emeraldInk),
                      SizedBox(width: 10),
                      Text(
                        'Push to talk',
                        style: TextStyle(
                          color: AppColors.emeraldInk,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              const Text(
                'Language',
                style: TextStyle(color: Color(0xFFD1DFD8), fontSize: 11),
              ),
              const SizedBox(width: 8),
              DropdownButton<String>(
                value: voice.language,
                dropdownColor: AppColors.emeraldInk,
                style: const TextStyle(color: AppColors.white, fontSize: 11),
                underline: const SizedBox.shrink(),
                items: const [
                  DropdownMenuItem(value: 'ur', child: Text('Urdu')),
                  DropdownMenuItem(value: 'en', child: Text('English')),
                ],
                onChanged: voice.isBusy
                    ? null
                    : (value) {
                        if (value != null) voice.setLanguage(value);
                      },
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            voice.errorMessage ?? 'Ready for a local recording.',
            style: const TextStyle(color: Color(0xFFD1DFD8), fontSize: 11),
          ),
        ],
      ),
    );
  }
}
