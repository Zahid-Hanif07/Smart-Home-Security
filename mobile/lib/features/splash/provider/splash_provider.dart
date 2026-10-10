import 'package:flutter/material.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/core/storage/local_storage.dart';
import 'package:mobile/providers/auth_provider.dart';

class SplashProvider extends ChangeNotifier {
  bool _started = false;

  Future<void> start(BuildContext context, AuthProvider authProvider) async {
    if (_started) return;
    _started = true;

    await Future.delayed(const Duration(milliseconds: 1500));
    if (!context.mounted) return;

    final onboardingCompleted = await LocalStorage.isOnboardingCompleted();
    if (!context.mounted) return;
    if (!onboardingCompleted) {
      Navigator.of(context).pushReplacementNamed(AppRoutes.onboarding);
      return;
    }

    final isAuthenticated = await authProvider.checkAuthStatus();
    if (!context.mounted) return;
    Navigator.of(context).pushReplacementNamed(
      isAuthenticated ? AppRoutes.home : AppRoutes.login,
    );
  }
}
