import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_text_styles.dart';

class AuthHeader extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;

  const AuthHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.icon = Icons.shield_outlined,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: AppColors.emeraldInk,
                borderRadius: BorderRadius.circular(15),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.emeraldInk.withValues(alpha: .14),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Icon(icon, size: 24, color: AppColors.lime),
            ),
            const SizedBox(width: 12),
            const Text(
              'OTTO',
              style: TextStyle(
                color: AppColors.emeraldInk,
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 3,
              ),
            ),
          ],
        ),
        const SizedBox(height: 25),
        Text(title, style: AppTextStyles.heading1),
        const SizedBox(height: 4),
        Text(subtitle, style: AppTextStyles.bodyMedium),
      ],
    );
  }
}
