import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';

void main() {
  group('ApiClient Tests', () {
    test('1. ApiClient construction and default configuration', () {
      final client = ApiClient();
      expect(client, isNotNull);
      expect(ApiConfig.baseUrl, isNotEmpty);
    });

    test('2. Successful GET /health check returns status ok', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/health');
        return http.Response('{"status": "ok"}', 200);
      });

      final apiClient = ApiClient(client: mockClient);
      final isHealthy = await apiClient.checkHealth();
      expect(isHealthy, isTrue);
    });

    test('3. Failed GET /health check handles offline server', () async {
      final mockClient = MockClient((request) async {
        return http.Response('Server Error', 500);
      });

      final apiClient = ApiClient(client: mockClient);
      final isHealthy = await apiClient.checkHealth();
      expect(isHealthy, isFalse);
    });

    test('4. API Exception status code mapping', () {
      final exc401 = ApiException.fromStatusCode(401, {'detail': 'Invalid token'});
      expect(exc401.statusCode, equals(401));
      expect(exc401.message, contains('Unauthorized access'));

      final exc403 = ApiException.fromStatusCode(403);
      expect(exc403.statusCode, equals(403));
      expect(exc403.message, contains("don't have permission"));
    });
  });
}
