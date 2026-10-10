import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide LocalStorage;
import 'package:mobile/app/theme/app_theme.dart';
import 'package:mobile/features/home/presentation/add_home_screen.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

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

  group('Home Management & Add Home Tests', () {
    testWidgets('Renders AddHomeScreen form fields', (WidgetTester tester) async {
      final authProvider = AuthProvider();
      final homeProvider = HomeProvider();

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
            ChangeNotifierProvider<HomeProvider>.value(value: homeProvider),
          ],
          child: MaterialApp(
            theme: AppTheme.lightTheme,
            home: const AddHomeScreen(),
          ),
        ),
      );

      expect(find.text('Add New Home'), findsOneWidget);
      expect(find.text('Property Information'), findsOneWidget);
      expect(find.text('Home / Property Name'), findsOneWidget);
      expect(find.text('Save & Select Home'), findsOneWidget);
    });
  });
}
