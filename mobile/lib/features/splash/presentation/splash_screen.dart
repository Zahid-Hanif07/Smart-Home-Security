import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/features/splash/provider/splash_provider.dart';
import 'package:mobile/providers/auth_provider.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1800),
  )..repeat(reverse: true);
  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: AppColors.emeraldInk,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<SplashProvider>().start(
        context,
        context.read<AuthProvider>(),
      );
    });
  }

  @override
  void dispose() {
    _motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reducedMotion = MediaQuery.disableAnimationsOf(context);
    return Scaffold(
      backgroundColor: AppColors.emeraldInk,
      body: Stack(
        children: [
          Positioned(
            top: MediaQuery.paddingOf(context).top + 20,
            left: 24,
            right: 24,
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'OTTO',
                  style: TextStyle(
                    color: AppColors.champagne,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 3,
                  ),
                ),
                Text(
                  'HOME SECURITY',
                  style: TextStyle(
                    color: Color(0xFFC2D4CB),
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.5,
                  ),
                ),
              ],
            ),
          ),
          Positioned(
            top: -100,
            right: -120,
            child: Container(
              width: 340,
              height: 340,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.forest.withValues(alpha: .6),
              ),
            ),
          ),
          Positioned(
            bottom: -170,
            left: -100,
            child: Container(
              width: 420,
              height: 420,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.forest.withValues(alpha: .35),
              ),
            ),
          ),
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedBuilder(
                  animation: _motion,
                  builder: (context, _) {
                    final t = reducedMotion ? 0.0 : _motion.value;
                    return SizedBox(
                      width: 150,
                      height: 150,
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          Transform.scale(
                            scale: 1 + t * .12,
                            child: Container(
                              width: 142,
                              height: 142,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: AppColors.champagne.withValues(
                                    alpha: .12 + .2 * (1 - t),
                                  ),
                                  width: 1.2,
                                ),
                              ),
                            ),
                          ),
                          Container(
                            width: 104,
                            height: 104,
                            decoration: BoxDecoration(
                              color: AppColors.champagne,
                              borderRadius: BorderRadius.circular(34),
                              boxShadow: [
                                BoxShadow(
                                  color: AppColors.champagne.withValues(
                                    alpha: .18,
                                  ),
                                  blurRadius: 34,
                                ),
                              ],
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(34),
                              child: Stack(
                                alignment: Alignment.center,
                                children: [
                                  const Icon(
                                    Icons.shield_rounded,
                                    size: 50,
                                    color: AppColors.emeraldInk,
                                  ),
                                  Positioned(
                                    left: 22,
                                    right: 22,
                                    top: 18 + 64 * t,
                                    child: Container(
                                      height: 1.5,
                                      color: AppColors.forest,
                                      foregroundDecoration: BoxDecoration(
                                        boxShadow: [
                                          BoxShadow(
                                            color: AppColors.forest.withValues(
                                              alpha: .6,
                                            ),
                                            blurRadius: 6,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
                const SizedBox(height: 27),
                const Text(
                  'OTTO',
                  style: TextStyle(
                    color: AppColors.champagne,
                    fontSize: 25,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 9,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'HOME SECURITY',
                  style: TextStyle(
                    color: Color(0xFFC2D4CB),
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 2.4,
                  ),
                ),
              ],
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 34,
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 24),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'SECURE SYSTEM',
                    style: TextStyle(
                      color: Color(0xFFC2D4CB),
                      fontSize: 9,
                      letterSpacing: 1.2,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  SizedBox(
                    width: 70,
                    child: LinearProgressIndicator(
                      borderRadius: BorderRadius.all(Radius.circular(9)),
                      minHeight: 2,
                      backgroundColor: Color(0x30F4ECD7),
                      color: AppColors.lime,
                    ),
                  ),
                  Text(
                    'INITIALIZING',
                    style: TextStyle(
                      color: Color(0xFFC2D4CB),
                      fontSize: 9,
                      letterSpacing: 1.2,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
