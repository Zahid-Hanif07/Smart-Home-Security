import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';

/// Presentational placeholder for the planned voice appliance controls.
class VoiceControlTeaser extends StatelessWidget {
  const VoiceControlTeaser({super.key});
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: AppColors.emeraldInk,
      borderRadius: BorderRadius.circular(22),
    ),
    child: Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.white.withValues(alpha: .12),
            borderRadius: BorderRadius.circular(16),
          ),
          child: const Icon(
            Icons.mic_none_rounded,
            color: AppColors.champagne,
            size: 25,
          ),
        ),
        const SizedBox(width: 14),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Voice control',
                style: TextStyle(
                  color: AppColors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Hands-free appliance controls are coming soon.',
                style: TextStyle(
                  color: Color(0xFFD1DFD8),
                  fontSize: 12,
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
          decoration: BoxDecoration(
            color: AppColors.champagne,
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Text(
            'SOON',
            style: TextStyle(
              color: AppColors.emeraldInk,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: .5,
            ),
          ),
        ),
      ],
    ),
  );
}
