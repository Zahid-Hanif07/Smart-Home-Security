import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/models/security_log_model.dart';
import 'package:mobile/providers/home_provider.dart';

void main() {
  group('HomeProvider Unit Tests', () {
    test('1. HomeProvider initial state', () {
      final homeProvider = HomeProvider();
      expect(homeProvider.isBackendConnected, isFalse);
      expect(homeProvider.isCheckingBackend, isFalse);
      expect(homeProvider.isLoading, isFalse);
      expect(homeProvider.isRefreshing, isFalse);
      expect(homeProvider.homes, isEmpty);
      expect(homeProvider.currentHome, isNull);
      expect(homeProvider.recentEvents, isEmpty);
      expect(homeProvider.securityStatus, equals(SecurityStatusState.offline));
    });

    test('2. Connection state updates via checkBackendHealth', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/health') {
          return http.Response('{"status": "ok"}', 200);
        }
        return http.Response('Not Found', 404);
      });

      final apiClient = ApiClient(client: mockClient);
      final homeProvider = HomeProvider(apiClient: apiClient);

      final isHealthy = await homeProvider.checkBackendHealth();
      expect(isHealthy, isTrue);
      expect(homeProvider.isBackendConnected, isTrue);
      expect(homeProvider.securityStatus, equals(SecurityStatusState.secure));
    });

    test('3. HomeProvider success loading homes and recent events', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/health') {
          return http.Response('{"status": "ok"}', 200);
        } else if (request.url.path == '/api/homes') {
          return http.Response('''[
            {
              "id": "11111111-1111-1111-1111-111111111111",
              "name": "Main Residence",
              "address": "123 Smart St"
            }
          ]''', 200);
        } else if (request.url.path.contains('/security-logs')) {
          return http.Response('''[
            {
              "id": "22222222-2222-2222-2222-222222222222",
              "home_id": "11111111-1111-1111-1111-111111111111",
              "event_type": "motion_detected",
              "description": "Motion detected in hallway",
              "created_at": "2026-09-30T12:00:00Z"
            }
          ]''', 200);
        }
        return http.Response('Not Found', 404);
      });

      final apiClient = ApiClient(client: mockClient);
      final homeProvider = HomeProvider(apiClient: apiClient);

      await homeProvider.loadHomeData('valid_token');

      expect(homeProvider.isBackendConnected, isTrue);
      expect(homeProvider.homes.length, equals(1));
      expect(homeProvider.currentHome?.name, equals('Main Residence'));
      expect(homeProvider.recentEvents.length, equals(1));
      expect(homeProvider.recentEvents.first.eventType, equals('motion_detected'));
      expect(homeProvider.securityStatus, equals(SecurityStatusState.unknownActivity));
    });

    test('4. HomeProvider API failure handling', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/health') {
          return http.Response('{"status": "ok"}', 200);
        }
        return http.Response('{"detail": "Server error"}', 500);
      });

      final apiClient = ApiClient(client: mockClient);
      final homeProvider = HomeProvider(apiClient: apiClient);

      await homeProvider.loadHomeData('valid_token');
      expect(homeProvider.isBackendConnected, isTrue);
      expect(homeProvider.errorMessage, isNotNull);
    });

    test('5. Refresh behavior updates state', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/health') {
          return http.Response('{"status": "ok"}', 200);
        } else if (request.url.path == '/api/homes') {
          return http.Response('[]', 200);
        }
        return http.Response('{"name": "Main Residence", "id": "11111111-1111-1111-1111-111111111111"}', 201);
      });

      final apiClient = ApiClient(client: mockClient);
      final homeProvider = HomeProvider(apiClient: apiClient);

      await homeProvider.refresh('token');
      expect(homeProvider.isBackendConnected, isTrue);
    });

    test('6. Security event parsing & formatting', () {
      final jsonLog = {
        'id': 'log-123',
        'home_id': 'home-456',
        'event_type': 'unknown_person',
        'description': 'Unrecognized intruder',
        'is_authorized': false,
        'created_at': '2026-09-30T10:00:00Z',
      };

      final log = SecurityLogModel.fromJson(jsonLog);
      expect(log.id, equals('log-123'));
      expect(log.eventType, equals('unknown_person'));
      expect(log.isAuthorized, isFalse);
      expect(log.displayTitle, equals('Unknown person detected'));
    });

    test('7. Empty event state yields secure status when backend online', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/health') {
          return http.Response('{"status": "ok"}', 200);
        } else if (request.url.path == '/api/homes') {
          return http.Response('''[
            {"id": "11111111-1111-1111-1111-111111111111", "name": "Main Residence"}
          ]''', 200);
        } else if (request.url.path.contains('/security-logs')) {
          return http.Response('[]', 200);
        }
        return http.Response('Not Found', 404);
      });

      final apiClient = ApiClient(client: mockClient);
      final homeProvider = HomeProvider(apiClient: apiClient);

      await homeProvider.loadHomeData('token');
      expect(homeProvider.recentEvents, isEmpty);
      expect(homeProvider.securityStatus, equals(SecurityStatusState.secure));
    });
  });
}
