import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/models/security_log_model.dart';

class ActivityItem extends StatelessWidget {
  final SecurityLogModel log;

  const ActivityItem({super.key, required this.log});

  String _formatTime(DateTime dateTime) {
    final local = dateTime.toLocal();
    final hour = local.hour > 12 ? local.hour - 12 : (local.hour == 0 ? 12 : local.hour);
    final minute = local.minute.toString().padLeft(2, '0');
    final period = local.hour >= 12 ? 'PM' : 'AM';
    return '$hour:$minute $period';
  }

  @override
  Widget build(BuildContext context) {
    final isAlert = log.eventType.toLowerCase() == 'unknown_person' || log.isAuthorized == false;
    final isAuthorized = log.eventType.toLowerCase() == 'authorized_person' || log.isAuthorized == true;

    IconData iconData = Icons.sensors_outlined;
    Color iconColor = AppColors.black;
    Color iconBgColor = AppColors.surfaceSoft;

    if (isAlert) {
      iconData = Icons.warning_amber_rounded;
      iconColor = AppColors.emeraldInk;
      iconBgColor = AppColors.champagne;
    } else if (isAuthorized) {
      iconData = Icons.person_outline_rounded;
      iconColor = AppColors.black;
      iconBgColor = AppColors.surfaceSoft;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Event Icon Badge
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: iconBgColor,
              shape: BoxShape.circle,
            ),
            child: Icon(
              iconData,
              size: 20,
              color: iconColor,
            ),
          ),
          const SizedBox(width: AppSpacing.md),

          // Details
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        log.displayTitle,
                        style: AppTextStyles.label.copyWith(
                          fontWeight: isAlert ? FontWeight.w700 : FontWeight.w600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      _formatTime(log.createdAt),
                      style: AppTextStyles.caption.copyWith(
                        color: AppColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
                if (log.description != null && log.description!.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    log.description!,
                    style: AppTextStyles.bodyMedium.copyWith(
                      color: AppColors.textSecondary,
                      fontSize: 13,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
