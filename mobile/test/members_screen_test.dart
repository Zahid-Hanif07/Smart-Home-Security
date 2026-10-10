import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:mobile/app/theme/app_theme.dart';
import 'package:mobile/features/members/presentation/members_screen.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
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

  testWidgets(
    'MembersScreen renders header banner and Add Member button without layout crash',
    (WidgetTester tester) async {
      final authProvider = AuthProvider();
      final homeProvider = HomeProvider();
      final membersProvider = MembersProvider();

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
            ChangeNotifierProvider<HomeProvider>.value(value: homeProvider),
            ChangeNotifierProvider<MembersProvider>.value(
              value: membersProvider,
            ),
          ],
          child: MaterialApp(
            theme: AppTheme.lightTheme,
            home: const MembersScreen(),
          ),
        ),
      );

      await tester.pump();

      // Verify title and Add Member button render without BoxConstraints infinite width error
      expect(find.text('Family Members'), findsOneWidget);
      expect(find.text('Add Member'), findsAtLeastNWidgets(1));
      expect(find.byType(ElevatedButton), findsAtLeastNWidgets(1));
    },
  );
}
