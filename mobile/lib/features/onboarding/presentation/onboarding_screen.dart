import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/features/onboarding/widgets/animated_get_started_button.dart';
import 'package:mobile/providers/onboarding_provider.dart';

/// Data model for onboarding slide content
class _OnboardingPageData {
  final String imagePath;
  final String title;
  final String description;

  const _OnboardingPageData({
    required this.imagePath,
    required this.title,
    required this.description,
  });
}

/// OTTO Onboarding Flow - Pure StatelessWidget
/// Renders 3-screen PageView flow with OTTO emerald & champagne aesthetic.
class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  static const List<_OnboardingPageData> _pages = [
    _OnboardingPageData(
      imagePath: 'assets/images/onboarding.png',
      title: 'Intelligent Vigilance',
      description:
          'Next-generation AI security monitoring your perimeter with precision and instant real-time awareness.',
    ),
    _OnboardingPageData(
      imagePath: 'assets/images/onboarding1.png',
      title: 'Biometric Recognition',
      description:
          'Advanced facial recognition and automated member verification for seamless, trusted access control.',
    ),
    _OnboardingPageData(
      imagePath: 'assets/images/onboarding2.png',
      title: 'Total Command',
      description:
          'Empower your home security with AI voice interaction, live threat telemetry, and real-time defense.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: AppColors.emeraldInk,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );

    final provider = Provider.of<OnboardingProvider>(context);

    return Scaffold(
      backgroundColor: AppColors.emeraldInk,
      body: SafeArea(
        child: Column(
          children: [
            // Top Header: App Branding & Skip Action
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.sm,
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // OTTO Champagne Wordmark
                  const Text(
                    'O T T O',
                    style: TextStyle(
                      color: AppColors.champagne,
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 4.0,
                    ),
                  ),
                  // Skip button on pages 1 & 2
                  if (!provider.isLastPage)
                    TextButton(
                      onPressed: () => provider.completeOnboarding(
                        context,
                        targetRoute: AppRoutes.login,
                      ),
                      style: TextButton.styleFrom(
                        foregroundColor: AppColors.champagne.withValues(alpha: 0.8),
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm,
                          vertical: AppSpacing.xs,
                        ),
                      ),
                      child: const Text(
                        'SKIP',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.5,
                        ),
                      ),
                    )
                  else
                    const SizedBox(height: 36),
                ],
              ),
            ),

            // Middle: PageView for Onboarding Content
            Expanded(
              child: PageView.builder(
                controller: provider.pageController,
                itemCount: _pages.length,
                onPageChanged: provider.onPageChanged,
                itemBuilder: (context, index) {
                  final item = _pages[index];
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        // Image Asset Container
                        Expanded(
                          flex: 6,
                          child: Center(
                            child: Padding(
                              padding: const EdgeInsets.all(AppSpacing.md),
                              child: Image.asset(
                                item.imagePath,
                                fit: BoxFit.contain,
                                errorBuilder: (context, error, stackTrace) {
                                  return const Icon(
                                    Icons.videocam_outlined,
                                    size: 80,
                                    color: AppColors.champagne,
                                  );
                                },
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),

                        // Text Details
                        Expanded(
                          flex: 3,
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.start,
                            children: [
                              Text(
                                item.title,
                                textAlign: TextAlign.center,
                                style: const TextStyle(
                                  color: AppColors.champagne,
                                  fontSize: 24,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1.0,
                                ),
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              Text(
                                item.description,
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: AppColors.white.withValues(alpha: 0.75),
                                  fontSize: 14,
                                  height: 1.45,
                                  fontWeight: FontWeight.w400,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),

            // Bottom Section: Page Indicator & Action Controls
            Padding(
              padding: const EdgeInsets.all(AppSpacing.xl),
              child: Column(
                children: [
                  // Dynamic Page Indicator Pills
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(
                      _pages.length,
                      (index) => AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        height: 8,
                        width: provider.currentPage == index ? 28 : 8,
                        decoration: BoxDecoration(
                          color: provider.currentPage == index
                              ? AppColors.champagne
                              : AppColors.champagne.withValues(alpha: 0.3),
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xl),

                  // Bottom Action Button
                  if (provider.isLastPage)
                    AnimatedGetStartedButton(
                      isNavigating: provider.isNavigating,
                      onPressed: () => provider.completeOnboarding(
                        context,
                        targetRoute: AppRoutes.login,
                      ),
                    )
                  else
                    SizedBox(
                      width: double.infinity,
                      height: 56,
                      child: ElevatedButton(
                        onPressed: provider.nextPage,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.champagne,
                          foregroundColor: AppColors.emeraldInk,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(28),
                          ),
                          elevation: 0,
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'NEXT',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 2.0,
                              ),
                            ),
                            SizedBox(width: 8),
                            Icon(
                              Icons.arrow_forward_rounded,
                              size: 18,
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
