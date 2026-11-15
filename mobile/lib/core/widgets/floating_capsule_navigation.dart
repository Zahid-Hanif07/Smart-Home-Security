import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';

/// Shared floating navigation for the main and account destinations.
class FloatingCapsuleNavigation extends StatelessWidget {
  final int selectedIndex;
  final bool profileMode;
  const FloatingCapsuleNavigation({
    super.key,
    required this.selectedIndex,
    this.profileMode = false,
  });

  @override
  Widget build(BuildContext context) => SafeArea(
    minimum: const EdgeInsets.fromLTRB(24, 0, 24, 10),
    child: ClipRRect(
      borderRadius: BorderRadius.circular(28),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          height: 64,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
          decoration: BoxDecoration(
            color: AppColors.surfaceTranslucent,
            borderRadius: BorderRadius.circular(28),
            border: Border.all(color: AppColors.border.withValues(alpha: .8)),
            boxShadow: [
              BoxShadow(
                color: AppColors.emeraldInk.withValues(alpha: .08),
                blurRadius: 24,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            children: [
              _item(
                context,
                0,
                Icons.home_outlined,
                Icons.home_rounded,
                'Home',
                AppRoutes.home,
              ),
              _item(
                context,
                1,
                Icons.people_outline_rounded,
                Icons.people_rounded,
                'People',
                AppRoutes.members,
              ),
              _item(
                context,
                2,
                Icons.home_work_outlined,
                Icons.home_work_rounded,
                'Homes',
                AppRoutes.homes,
              ),
              _item(
                context,
                3,
                profileMode
                    ? Icons.person_outline_rounded
                    : Icons.notifications_none_rounded,
                profileMode
                    ? Icons.person_rounded
                    : Icons.notifications_rounded,
                profileMode ? 'Profile' : 'Alerts',
                profileMode ? AppRoutes.profile : AppRoutes.alerts,
              ),
            ],
          ),
        ),
      ),
    ),
  );

  Widget _item(
    BuildContext context,
    int index,
    IconData icon,
    IconData activeIcon,
    String label,
    String route,
  ) {
    final selected = selectedIndex == index;
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: selected ? null : () => Navigator.of(context).pushNamed(route),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          decoration: BoxDecoration(
            color: selected ? AppColors.champagne : Colors.transparent,
            borderRadius: BorderRadius.circular(22),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                selected ? activeIcon : icon,
                size: 20,
                color: selected ? AppColors.emeraldInk : AppColors.textMuted,
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  color: selected ? AppColors.emeraldInk : AppColors.textMuted,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
