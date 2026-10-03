import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/providers/auth_provider.dart';

/// Splash Screen - StatelessWidget implementation
/// Renders modern minimalist identity and triggers AuthProvider session verification.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  void _checkAuthAndNavigate(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      
      // Give splash a brief elegant pulse
      await Future.delayed(const Duration(milliseconds: 600));
      if (!context.mounted) return;

      final isAuthenticated = await authProvider.checkAuthStatus();
      if (!context.mounted) return;

      if (isAuthenticated) {
        Navigator.of(context).pushReplacementNamed(AppRoutes.home);
      } else {
        Navigator.of(context).pushReplacementNamed(AppRoutes.login);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    _checkAuthAndNavigate(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              // Refined minimalist shield emblem with soft pink accent background
              Container(
                padding: const EdgeInsets.all(AppSpacing.lg),
                decoration: BoxDecoration(
                  color: AppColors.champagne,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: AppColors.emeraldInk.withValues(alpha: 0.3),
                    width: 1.5,
                  ),
                ),
                child: const Icon(
                  Icons.shield_outlined,
                  size: 48,
                  color: AppColors.black,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              const Text(
                'SMART HOME SECURITY',
                style: AppTextStyles.heading2,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.xs),
              const Text(
                'AI Security & Voice Assistant Mobile Engine',
                style: AppTextStyles.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const Spacer(),
              // Minimal progress indicator
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2.0,
                  color: AppColors.black,
                ),
              ),
              const SizedBox(height: AppSpacing.xxl),
            ],
          ),
        ),
      ),
    );
  }
}
