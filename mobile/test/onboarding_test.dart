import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide LocalStorage;
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/core/storage/local_storage.dart';
import 'package:mobile/providers/onboarding_provider.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/features/splash/presentation/splash_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    try {
      await Supabase.initialize(
        url: 'https://example.supabase.co',
        anonKey: 'mock_anon_key',
      );
    } catch (_) {}
  });

  group('OnboardingProvider Tests', () {
    test('Initial page index is 0 and isLastPage is false', () {
      final provider = OnboardingProvider();
      expect(provider.currentPage, equals(0));
      expect(provider.isLastPage, isFalse);
      expect(provider.isNavigating, isFalse);
    });

    test('onPageChanged updates page index correctly', () {
      final provider = OnboardingProvider();
      provider.onPageChanged(1);
      expect(provider.currentPage, equals(1));
      expect(provider.isLastPage, isFalse);

      provider.onPageChanged(2);
      expect(provider.currentPage, equals(2));
      expect(provider.isLastPage, isTrue);
    });

    test('completeOnboarding sets local storage flag', () async {
      expect(await LocalStorage.isOnboardingCompleted(), isFalse);

      await LocalStorage.setOnboardingCompleted(true);
      expect(await LocalStorage.isOnboardingCompleted(), isTrue);
    });
  });

  group('Widget Tests for Onboarding and Splash', () {
    testWidgets(
      'OnboardingScreen renders title, images, indicators, and buttons',
      (tester) async {
        await tester.pumpWidget(
          MultiProvider(
            providers: [
              ChangeNotifierProvider<OnboardingProvider>(
                create: (_) => OnboardingProvider(),
              ),
              ChangeNotifierProvider<AuthProvider>(
                create: (_) => AuthProvider(),
              ),
            ],
            child: MaterialApp(
              initialRoute: AppRoutes.onboarding,
              routes: AppRoutes.routes,
            ),
          ),
        );

        // Verify OTTO branding and first page title
        expect(find.text('O T T O'), findsOneWidget);
        expect(find.text('Intelligent Vigilance'), findsOneWidget);
        expect(find.text('SKIP'), findsOneWidget);
        expect(find.text('NEXT'), findsOneWidget);
      },
    );

    testWidgets('SplashScreen renders splash image', (tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<OnboardingProvider>(
              create: (_) => OnboardingProvider(),
            ),
            ChangeNotifierProvider<AuthProvider>(create: (_) => AuthProvider()),
          ],
          child: MaterialApp(
            initialRoute: AppRoutes.splash,
            routes: AppRoutes.routes,
          ),
        ),
      );

      expect(find.byType(SplashScreen), findsOneWidget);
      expect(find.byType(Image), findsOneWidget);
      await tester.pump(const Duration(seconds: 2));
    });
  });
}
