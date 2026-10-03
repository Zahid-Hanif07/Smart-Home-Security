import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/features/home/widgets/home_header.dart';
import 'package:mobile/features/home/widgets/security_status_card.dart';
import 'package:mobile/features/home/widgets/backend_connection_card.dart';
import 'package:mobile/features/home/widgets/live_camera_preview.dart';
import 'package:mobile/features/home/widgets/recent_activity.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

/// HomeScreen - Step 10 & 11 Real Mobile Security Dashboard (StatelessWidget)
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  void _initHomeState(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final homeProvider = Provider.of<HomeProvider>(context, listen: false);
      final authProvider = Provider.of<AuthProvider>(context, listen: false);

      if (!homeProvider.isBackendConnected && !homeProvider.isCheckingBackend) {
        await homeProvider.loadHomeData(authProvider.token);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    _initHomeState(context);

    final authProvider = Provider.of<AuthProvider>(context);
    final homeProvider = Provider.of<HomeProvider>(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.black,
          backgroundColor: AppColors.surface,
          onRefresh: () async {
            await homeProvider.refresh(authProvider.token);
          },
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.md,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 1. Mobile Header (Home Identity & Profile)
                HomeHeader(
                  user: authProvider.currentUser,
                  homeName: homeProvider.currentHome?.name ?? 'Main Residence',
                  isBackendConnected: homeProvider.isBackendConnected,
                  onLogout: () async {
                    await authProvider.logout();
                    if (context.mounted) {
                      Navigator.of(context).pushReplacementNamed(AppRoutes.login);
                    }
                  },
                ),
                const SizedBox(height: AppSpacing.md),

                // 2. Subtle Backend Connection Status Indicator
                BackendConnectionCard(
                  isConnected: homeProvider.isBackendConnected,
                  isChecking: homeProvider.isCheckingBackend,
                  onTestConnection: () async {
                    await homeProvider.loadHomeData(authProvider.token);
                  },
                ),
                const SizedBox(height: AppSpacing.md),

                // 3. Security Overview Status
                SecurityStatusCard(
                  homeName: homeProvider.currentHome?.name ?? 'Main Residence',
                  status: homeProvider.securityStatus,
                  eventCount: homeProvider.recentEvents.length,
                ),
                const SizedBox(height: AppSpacing.md),

                // 4. Step 11 Family Members Navigation Tile
                Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: InkWell(
                    onTap: () {
                      Navigator.of(context).pushNamed(AppRoutes.members);
                    },
                    borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.md),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: const BoxDecoration(
                              color: AppColors.champagne,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.people_alt_rounded,
                              color: AppColors.black,
                              size: 22,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.md),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Family Members & Faces',
                                  style: TextStyle(
                                    color: AppColors.textPrimary,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                SizedBox(height: 2),
                                Text(
                                  'Manage authorized people & face recognition',
                                  style: TextStyle(
                                    color: AppColors.textSecondary,
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.chevron_right_rounded,
                            color: AppColors.textMuted,
                            size: 22,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.md),

                // 5. Live Camera MJPEG Viewport
                LiveCameraPreview(
                  isBackendConnected: homeProvider.isBackendConnected,
                  onRetryConnection: () async {
                    await homeProvider.loadHomeData(authProvider.token);
                  },
                ),
                const SizedBox(height: AppSpacing.md),

                // 6. Real Recent Security Activity Section
                RecentActivity(
                  events: homeProvider.recentEvents,
                  isLoading: homeProvider.isLoading,
                  isConnected: homeProvider.isBackendConnected,
                ),
                const SizedBox(height: AppSpacing.xl),
              ],
            ),
          ),
        ),
      ),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          indicatorColor: AppColors.champagne,
          backgroundColor: AppColors.surface,
          labelTextStyle: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const TextStyle(
                color: AppColors.black,
                fontWeight: FontWeight.w700,
                fontSize: 12,
              );
            }
            return const TextStyle(
              color: AppColors.textMuted,
              fontWeight: FontWeight.w500,
              fontSize: 12,
            );
          }),
          iconTheme: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const IconThemeData(color: AppColors.black, size: 22);
            }
            return const IconThemeData(color: AppColors.textMuted, size: 22);
          }),
        ),
        child: NavigationBar(
          selectedIndex: 0,
          elevation: 0,
          height: 64,
          onDestinationSelected: (index) {
            if (index == 1) {
              Navigator.of(context).pushNamed(AppRoutes.members);
            }
          },
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'Home',
            ),
            NavigationDestination(
              icon: Icon(Icons.people_outline_rounded),
              selectedIcon: Icon(Icons.people_rounded),
              label: 'Members',
            ),
            NavigationDestination(
              icon: Icon(Icons.tune_outlined),
              selectedIcon: Icon(Icons.tune_rounded),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}
