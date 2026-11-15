import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_theme.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';
import 'package:mobile/providers/onboarding_provider.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/features/splash/provider/splash_provider.dart';
import 'package:mobile/features/home/provider/camera_stream_provider.dart';
import 'package:mobile/features/home/provider/alerts_provider.dart';
import 'package:mobile/features/home/provider/face_occlusion_provider.dart';
import 'package:mobile/features/voice/provider/voice_provider.dart';
import 'package:mobile/features/voice/services/offline_whisper_service.dart';

class SmartHomeApp extends StatelessWidget {
  const SmartHomeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>(create: (_) => AuthProvider()),
        ChangeNotifierProvider<HomeProvider>(create: (_) => HomeProvider()),
        ChangeNotifierProvider<CameraStreamProvider>(create: (_) => CameraStreamProvider()),
        ChangeNotifierProvider<AlertsProvider>(create: (_) => AlertsProvider()),
        ChangeNotifierProvider<FaceOcclusionProvider>(
          create: (_) => FaceOcclusionProvider(),
        ),
        ChangeNotifierProvider<VoiceProvider>(
          create: (_) => VoiceProvider(recognizer: OfflineWhisperService()),
        ),
        ChangeNotifierProvider<MembersProvider>(
          create: (_) => MembersProvider(),
        ),
        ChangeNotifierProvider<OnboardingProvider>(
          create: (_) => OnboardingProvider(),
        ),
        ChangeNotifierProvider<SplashProvider>(create: (_) => SplashProvider()),
      ],
      child: MaterialApp(
        title: 'Smart Home Security',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        initialRoute: AppRoutes.splash,
        routes: AppRoutes.routes,
        navigatorObservers: [AppRoutes.observer],
      ),
    );
  }
}
