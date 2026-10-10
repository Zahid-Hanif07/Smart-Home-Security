import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/core/widgets/subtle_blur_card.dart';
import 'package:mobile/models/user_model.dart';

import 'package:mobile/app/routes/app_routes.dart';

class HomeHeader extends StatelessWidget {
  final UserModel? user;
  final String homeName;
  final bool isBackendConnected;
  final VoidCallback onLogout;

  const HomeHeader({
    super.key,
    required this.user,
    required this.homeName,
    required this.isBackendConnected,
    required this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    final initial = user?.name.isNotEmpty == true
        ? user!.name.substring(0, 1).toUpperCase()
        : 'H';

    return SubtleBlurCard(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        children: [
          // User avatar badge with soft champagne accent container
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: AppColors.champagne,
              shape: BoxShape.circle,
              border: Border.all(
                color: AppColors.emeraldInk.withValues(alpha: 0.3),
                width: 1.0,
              ),
            ),
            alignment: Alignment.center,
            child: Text(
              initial,
              style: AppTextStyles.heading3.copyWith(
                color: AppColors.black,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: InkWell(
              onTap: () {
                Navigator.of(context).pushNamed(AppRoutes.homes);
              },
              borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          homeName,
                          style: AppTextStyles.heading3,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Icon(Icons.swap_horiz_rounded, size: 16, color: AppColors.emeraldInk),
                      const SizedBox(width: 4),
                      Container(
                        width: 7,
                        height: 7,
                        decoration: BoxDecoration(
                          color: isBackendConnected ? AppColors.success : AppColors.error,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    user != null ? 'Owner: ${user!.name}' : 'Smart Home Security',
                    style: AppTextStyles.caption.copyWith(color: AppColors.textSecondary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ),
          IconButton(
            icon: const Icon(
              Icons.logout_rounded,
              color: AppColors.black,
              size: 20,
            ),
            tooltip: 'Sign Out',
            onPressed: onLogout,
          ),
        ],
      ),
    );
  }
}
