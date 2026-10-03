import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/providers/auth_provider.dart';

void main() {
  group('AuthProvider Tests', () {
    test('1. AuthProvider starts unauthenticated with no user', () {
      final authProvider = AuthProvider();
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.currentUser, isNull);
      expect(authProvider.token, isNull);
      expect(authProvider.errorMessage, isNull);
    });

    test('2. Successful login updates currentUser and token', () async {
      final authProvider = AuthProvider();
      final success = await authProvider.login('user@example.com', 'password123');

      expect(success, isTrue);
      expect(authProvider.isAuthenticated, isTrue);
      expect(authProvider.currentUser, isNotNull);
      expect(authProvider.currentUser!.email, equals('user@example.com'));
      expect(authProvider.token, isNotNull);
    });

    test('3. Empty credentials produce login error state', () async {
      final authProvider = AuthProvider();
      final success = await authProvider.login('', '');

      expect(success, isFalse);
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.errorMessage, isNotNull);
      expect(authProvider.errorMessage, contains('Please enter both email and password'));
    });

    test('4. Logout resets authentication state cleanly', () async {
      final authProvider = AuthProvider();
      await authProvider.login('user@example.com', 'password123');
      expect(authProvider.isAuthenticated, isTrue);

      await authProvider.logout();
      expect(authProvider.isAuthenticated, isFalse);
      expect(authProvider.currentUser, isNull);
      expect(authProvider.token, isNull);
    });
  });
}
