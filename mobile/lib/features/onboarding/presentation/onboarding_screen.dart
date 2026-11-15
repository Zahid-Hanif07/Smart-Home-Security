import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/providers/onboarding_provider.dart';

class _OnboardingPageData {
  final IconData icon;
  final String tag, eyebrow, title, description;
  const _OnboardingPageData({
    required this.icon,
    required this.tag,
    required this.eyebrow,
    required this.title,
    required this.description,
  });
}

class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  static const List<_OnboardingPageData> _pages = [
    _OnboardingPageData(
      icon: Icons.center_focus_strong_rounded,
      tag: 'Intelligent vigilance',
      eyebrow: 'Always aware',
      title: 'Protection that\npays attention.',
      description:
          'Know what’s happening around your home with real-time security awareness.',
    ),
    _OnboardingPageData(
      icon: Icons.face_retouching_natural_rounded,
      tag: 'Biometric recognition',
      eyebrow: 'Trusted people',
      title: 'Familiar faces.\nClear decisions.',
      description:
          'Enroll the people you trust and review recognition activity from your phone.',
    ),
    _OnboardingPageData(
      icon: Icons.dashboard_customize_rounded,
      tag: 'One clear command center',
      eyebrow: 'Control from anywhere',
      title: 'Your home.\nUnder your care.',
      description:
          'Bring camera, people, and important events into one focused security dashboard.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        systemNavigationBarColor: AppColors.background,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
    );
    final provider = context.watch<OnboardingProvider>();
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'OTTO',
                    style: TextStyle(
                      color: AppColors.emeraldInk,
                      letterSpacing: 4,
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  if (!provider.isLastPage)
                    TextButton(
                      onPressed: () => provider.completeOnboarding(
                        context,
                        targetRoute: AppRoutes.login,
                      ),
                      child: const Text(
                        'SKIP',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          letterSpacing: 1.4,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    )
                  else
                    const SizedBox(width: 48),
                ],
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: provider.pageController,
                itemCount: _pages.length,
                onPageChanged: provider.onPageChanged,
                itemBuilder: (context, index) {
                  final page = _pages[index];
                  return Padding(
                    padding: const EdgeInsets.fromLTRB(20, 5, 20, 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 6,
                          child: Container(
                            width: double.infinity,
                            margin: const EdgeInsets.only(bottom: 20),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(26),
                              gradient: const RadialGradient(
                                colors: [Color(0xFFE2ECD9), Color(0xFFF5ECD9)],
                                radius: 1.0,
                              ),
                            ),
                            child: Stack(
                              alignment: Alignment.center,
                              children: [
                                Container(
                                  width: 164,
                                  height: 164,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: AppColors.emeraldInk.withValues(
                                        alpha: .22,
                                      ),
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: AppColors.emeraldInk.withValues(
                                          alpha: .04,
                                        ),
                                        blurRadius: 0,
                                        spreadRadius: 18,
                                      ),
                                      BoxShadow(
                                        color: AppColors.emeraldInk.withValues(
                                          alpha: .025,
                                        ),
                                        blurRadius: 0,
                                        spreadRadius: 38,
                                      ),
                                    ],
                                  ),
                                ),
                                Container(
                                  width: 76,
                                  height: 76,
                                  decoration: BoxDecoration(
                                    color: AppColors.emeraldInk,
                                    borderRadius: BorderRadius.circular(25),
                                    boxShadow: [
                                      BoxShadow(
                                        color: AppColors.emeraldInk.withValues(
                                          alpha: .18,
                                        ),
                                        blurRadius: 28,
                                        offset: const Offset(0, 12),
                                      ),
                                    ],
                                  ),
                                  child: Icon(
                                    page.icon,
                                    size: 36,
                                    color: AppColors.champagne,
                                  ),
                                ),
                                Positioned(
                                  left: 16,
                                  bottom: 15,
                                  child: Text(
                                    page.tag.toUpperCase(),
                                    style: const TextStyle(
                                      color: AppColors.textSecondary,
                                      fontSize: 9,
                                      letterSpacing: 1.2,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                page.eyebrow.toUpperCase(),
                                style: const TextStyle(
                                  color: AppColors.forest,
                                  fontSize: 10,
                                  letterSpacing: 1.2,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                page.title,
                                style: const TextStyle(
                                  fontSize: 29,
                                  height: 1.12,
                                  letterSpacing: -1,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                page.description,
                                style: const TextStyle(
                                  fontSize: 13,
                                  height: 1.5,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                      ],
                    ),
                  );
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List.generate(
                      _pages.length,
                      (index) => AnimatedContainer(
                        duration: const Duration(milliseconds: 220),
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        width: provider.currentPage == index ? 20 : 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: provider.currentPage == index
                              ? AppColors.emeraldInk
                              : const Color(0xFFC4CEC4),
                          borderRadius: BorderRadius.circular(9),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    height: 46,
                    child: ElevatedButton(
                      onPressed: provider.isLastPage
                          ? (provider.isNavigating
                                ? null
                                : () => provider.completeOnboarding(
                                    context,
                                    targetRoute: AppRoutes.login,
                                  ))
                          : provider.nextPage,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.emeraldInk,
                        foregroundColor: AppColors.champagne,
                        minimumSize: const Size.fromHeight(46),
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        shape: const StadiumBorder(),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            provider.isLastPage ? 'GET STARTED' : 'NEXT',
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.1,
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Icon(Icons.arrow_forward_rounded, size: 16),
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
