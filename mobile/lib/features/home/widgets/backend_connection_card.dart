import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/core/config/api_config.dart';

class BackendConnectionCard extends StatelessWidget {
  final bool isConnected;
  final bool isChecking;
  final VoidCallback onTestConnection;

  const BackendConnectionCard({
    super.key,
    required this.isConnected,
    required this.isChecking,
    required this.onTestConnection,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = isConnected ? AppColors.success : AppColors.error;
    final statusText = isChecking ? 'CONNECTING' : (isConnected ? 'ONLINE' : 'OFFLINE');

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm + 4,
      ),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        border: Border.all(color: AppColors.border, width: 1.0),
      ),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: isChecking ? AppColors.warning : statusColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      'FastAPI Engine',
                      style: AppTextStyles.label,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '($statusText)',
                      style: AppTextStyles.caption.copyWith(
                        color: isChecking ? AppColors.warning : statusColor,
                        fontWeight: FontWeight.w600,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
                Text(
                  ApiConfig.baseUrl,
                  style: AppTextStyles.caption.copyWith(
                    color: AppColors.textMuted,
                    fontSize: 11,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          InkWell(
            onTap: isChecking ? null : onTestConnection,
            borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
            child: Padding(
              padding: const EdgeInsets.all(6.0),
              child: isChecking
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 1.8,
                        valueColor: AlwaysStoppedAnimation<Color>(AppColors.black),
                      ),
                    )
                  : const Icon(
                      Icons.refresh_rounded,
                      size: 18,
                      color: AppColors.textSecondary,
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
