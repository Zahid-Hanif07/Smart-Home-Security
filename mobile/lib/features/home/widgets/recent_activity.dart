import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/features/home/widgets/activity_item.dart';
import 'package:mobile/models/security_log_model.dart';

class RecentActivity extends StatelessWidget {
  final List<SecurityLogModel> events;
  final bool isLoading;
  final bool isConnected;

  const RecentActivity({
    super.key,
    required this.events,
    required this.isLoading,
    required this.isConnected,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        border: Border.all(color: AppColors.border, width: 1.0),
      ),
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Recent Activity',
                style: AppTextStyles.heading3,
              ),
              if (events.isNotEmpty)
                Text(
                  '${events.length} events',
                  style: AppTextStyles.caption.copyWith(color: AppColors.textMuted),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          const Divider(height: 1, color: AppColors.borderSubtle),
          const SizedBox(height: AppSpacing.sm),

          if (!isConnected)
            _buildEmptyContainer(
              icon: Icons.wifi_off_rounded,
              title: 'Backend Disconnected',
              subtitle: 'Connect to FastAPI to view real-time security events.',
            )
          else if (isLoading && events.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.lg),
              child: Center(
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.0,
                    valueColor: AlwaysStoppedAnimation<Color>(AppColors.black),
                  ),
                ),
              ),
            )
          else if (events.isEmpty)
            _buildEmptyContainer(
              icon: Icons.shield_outlined,
              title: 'No recent security activity',
              subtitle: 'Your home security events will appear here.',
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: events.length,
              separatorBuilder: (context, index) => const Divider(height: 1, color: AppColors.borderSubtle),
              itemBuilder: (context, index) {
                return ActivityItem(log: events[index]);
              },
            ),
        ],
      ),
    );
  }

  Widget _buildEmptyContainer({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.lg, horizontal: AppSpacing.md),
      child: Center(
        child: Column(
          children: [
            Icon(icon, size: 28, color: AppColors.textMuted),
            const SizedBox(height: AppSpacing.sm),
            Text(
              title,
              style: AppTextStyles.label.copyWith(color: AppColors.textPrimary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: AppTextStyles.caption.copyWith(color: AppColors.textMuted),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
