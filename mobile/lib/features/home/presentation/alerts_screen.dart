import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/core/widgets/floating_capsule_navigation.dart';
import 'package:mobile/features/home/provider/alerts_provider.dart';
import 'package:mobile/features/home/widgets/alerts_section.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

/// Full alerts view reuses the same provider and alert actions as the dashboard.
class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final home = context.watch<HomeProvider>();
    final auth = context.watch<AuthProvider>();
    final alerts = context.watch<AlertsProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      alerts.load(home.currentHome?.id, auth.token);
    });
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'OTTO',
          style: TextStyle(
            letterSpacing: 3,
            fontWeight: FontWeight.w800,
            color: AppColors.emeraldInk,
          ),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: CircleAvatar(
              radius: 17,
              backgroundColor: AppColors.champagne,
              foregroundColor: AppColors.emeraldInk,
              child: Text(
                (auth.currentUser?.name.isNotEmpty ?? false)
                    ? auth.currentUser!.name[0].toUpperCase()
                    : 'H',
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        children: [
          const Text(
            'SECURITY ACTIVITY',
            style: TextStyle(
              fontSize: 10,
              letterSpacing: 1.2,
              fontWeight: FontWeight.w700,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 5),
          const Text(
            'Alerts',
            style: TextStyle(
              fontSize: 28,
              height: 1.15,
              fontWeight: FontWeight.w700,
              letterSpacing: -.7,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            alerts.unreadCount == 0
                ? 'You’re up to date.'
                : '${alerts.unreadCount} unread security ${alerts.unreadCount == 1 ? 'alert' : 'alerts'}.',
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 16),
          AlertsSection(homeId: home.currentHome?.id, token: auth.token),
        ],
      ),
      bottomNavigationBar: const FloatingCapsuleNavigation(selectedIndex: 3),
    );
  }
}
