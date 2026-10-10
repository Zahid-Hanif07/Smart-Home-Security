import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide LocalStorage;
import 'package:mobile/providers/auth_provider.dart';

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

  group('AuthProvider Tests', () {
    test('1. AuthProvider starts unauthenticated with no user', () {
      final authProvider = AuthProvider();
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.currentUser, isNull);
      expect(authProvider.token, isNull);
      expect(authProvider.errorMessage, isNull);
    });

    test('2. Empty credentials produce login error state', () async {
      final authProvider = AuthProvider();
      final success = await authProvider.login('', '');

      expect(success, isFalse);
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.errorMessage, isNotNull);
      expect(authProvider.errorMessage, contains('Please enter both email and password'));
    });

    test('3. Logout resets authentication state cleanly', () async {
      final authProvider = AuthProvider();
      await authProvider.logout();
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.currentUser, isNull);
      expect(authProvider.token, isNull);
    });
  });
}
