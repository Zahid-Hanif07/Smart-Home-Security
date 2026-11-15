import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide LocalStorage;
import 'package:mobile/features/auth/presentation/register_screen.dart';
import 'package:mobile/providers/auth_provider.dart';

class _PendingConfirmationProvider extends AuthProvider {
  _PendingConfirmationProvider() : super();
  bool pending = false;

  @override
  bool get isConfirmationPending => pending;

  @override
  Future<bool> register(String name, String email, String password) async {
    pending = true;
    notifyListeners();
    return true;
  }
}

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

  testWidgets('email confirmation keeps user on setup and does not report login', (tester) async {
    final provider = _PendingConfirmationProvider();
    await tester.pumpWidget(
      ChangeNotifierProvider<AuthProvider>.value(
        value: provider,
        child: const MaterialApp(home: RegisterScreen()),
      ),
    );
    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), 'Test User');
    await tester.enterText(fields.at(1), 'test@example.com');
    await tester.enterText(fields.at(2), 'password123');
    await tester.enterText(fields.at(3), 'password123');
    await tester.ensureVisible(find.text('Register Account'));
    await tester.tap(find.text('Register Account'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Confirm your email'), findsOneWidget);
    expect(find.text('Make home\nfeel safer.'), findsOneWidget);
  });
}
