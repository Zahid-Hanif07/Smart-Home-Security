import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/providers/home_provider.dart';

class SecurityStatusCard extends StatelessWidget {
  final String homeName;
  final SecurityStatusState status;
  final int eventCount;

  const SecurityStatusCard({
    super.key,
    required this.homeName,
    required this.status,
    this.eventCount = 0,
  });

  @override
  Widget build(BuildContext context) {
    String badgeText;
    String statusTitle;
    String statusSubtitle;
    IconData iconData;
    Color badgeBg;
    Color badgeTextColor;

    switch (status) {
      case SecurityStatusState.secure:
        badgeText = 'SECURE';
        statusTitle = 'System Protected';
        statusSubtitle = 'All security monitoring active';
        iconData = Icons.shield_outlined;
        badgeBg = AppColors.champagne;
        badgeTextColor = AppColors.emeraldInk;
        break;
      case SecurityStatusState.alert:
        badgeText = 'ALERT';
        statusTitle = 'Unrecognized Person Detected';
        statusSubtitle = 'Unknown entity detected on live camera';
        iconData = Icons.warning_amber_rounded;
        badgeBg = AppColors.champagne;
        badgeTextColor = AppColors.emeraldInk;
        break;
      case SecurityStatusState.unknownActivity:
        badgeText = 'ACTIVITY';
        statusTitle = 'Motion Activity Detected';
        statusSubtitle = 'Recent motion logged by security engine';
        iconData = Icons.motion_photos_on_outlined;
        badgeBg = AppColors.surfaceSoft;
        badgeTextColor = AppColors.black;
        break;
      case SecurityStatusState.offline:
        badgeText = 'OFFLINE';
        statusTitle = 'Security System Offline';
        statusSubtitle = 'FastAPI backend connection unreachable';
        iconData = Icons.wifi_off_rounded;
        badgeBg = AppColors.surfaceSoft;
        badgeTextColor = AppColors.textMuted;
        break;
    }

    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        border: Border.all(color: AppColors.border, width: 1.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: badgeBg,
                  borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
                ),
                child: Icon(
                  iconData,
                  size: 22,
                  color: badgeTextColor,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      statusTitle,
                      style: AppTextStyles.heading3,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      statusSubtitle,
                      style: AppTextStyles.caption.copyWith(color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: badgeBg,
                  borderRadius: BorderRadius.circular(AppSpacing.radiusPill),
                  border: Border.all(
                    color: badgeTextColor.withValues(alpha: 0.2),
                    width: 1.0,
                  ),
                ),
                child: Text(
                  badgeText,
                  style: AppTextStyles.caption.copyWith(
                    color: badgeTextColor,
                    fontWeight: FontWeight.w700,
                    fontSize: 10,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
