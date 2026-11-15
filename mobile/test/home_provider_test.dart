import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/models/pairing_code_model.dart';
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
        } else if (request.url.path == '/api/auth/me') {
          return http.Response(
            '{"id":"user-1","name":"Test","email":"test@example.com","created_at":"2026-01-01T00:00:00Z"}',
            200,
          );
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
      expect(
        homeProvider.recentEvents.first.eventType,
        equals('motion_detected'),
      );
      expect(
        homeProvider.securityStatus,
        equals(SecurityStatusState.unknownActivity),
      );
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
        return http.Response(
          '{"name": "Main Residence", "id": "11111111-1111-1111-1111-111111111111"}',
          201,
        );
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

    test(
      '7. Empty event state yields secure status when backend online',
      () async {
        final mockClient = MockClient((request) async {
          if (request.url.path == '/health') {
            return http.Response('{"status": "ok"}', 200);
          } else if (request.url.path == '/api/auth/me') {
            return http.Response(
              '{"id":"user-1","name":"Test","email":"test@example.com","created_at":"2026-01-01T00:00:00Z"}',
              200,
            );
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
      },
    );

    test(
      '8. Initial setup verifies profile and creates a home only once',
      () async {
        var storedHome = <String, dynamic>{};
        var createCount = 0;
        final apiClient = ApiClient(
          client: MockClient((request) async {
            if (request.url.path == '/api/auth/me') {
              return http.Response(
                '{"id":"user-1","name":"Test","email":"test@example.com","created_at":"2026-01-01T00:00:00Z"}',
                200,
              );
            }
            if (request.url.path == '/api/homes' && request.method == 'GET') {
              return http.Response(
                storedHome.isEmpty ? '[]' : '[${jsonEncode(storedHome)}]',
                200,
              );
            }
            if (request.url.path == '/api/homes/initial' &&
                request.method == 'POST') {
              createCount++;
              storedHome = {
                'id': 'home-1',
                'owner_id': 'user-1',
                'name': 'Main Residence',
                'created_at': '2026-01-01T00:00:00Z',
              };
              return http.Response(jsonEncode(storedHome), 200);
            }
            return http.Response('Not Found', 404);
          }),
        );
        final provider = HomeProvider(apiClient: apiClient);

        expect(await provider.setupHomesForAuthenticatedUser('token'), isTrue);
        expect(await provider.setupHomesForAuthenticatedUser('token'), isTrue);
        expect(createCount, 1);
        expect(provider.currentHome?.id, 'home-1');
        expect(provider.homes, hasLength(1));
      },
    );

    test('9. Home setup exposes a failed persistent write for retry', () async {
      final apiClient = ApiClient(
        client: MockClient((request) async {
          if (request.url.path == '/api/auth/me') {
            return http.Response(
              '{"id":"user-1","name":"Test","email":"test@example.com","created_at":"2026-01-01T00:00:00Z"}',
              200,
            );
          }
          if (request.url.path == '/api/homes') return http.Response('[]', 200);
          if (request.url.path == '/api/homes/initial') {
            return http.Response('{"detail":"Supabase write failed"}', 503);
          }
          return http.Response('Not Found', 404);
        }),
      );
      final provider = HomeProvider(apiClient: apiClient);

      expect(await provider.setupHomesForAuthenticatedUser('token'), isFalse);
      expect(provider.currentHome, isNull);
      expect(provider.errorMessage, isNotNull);
    });

    test(
      'generates a pairing code for a verified home using owner Bearer auth',
      () async {
        http.Request? pairingRequest;
        final apiClient = ApiClient(
          client: MockClient((request) async {
            if (request.method == 'GET' && request.url.path == '/api/homes') {
              return http.Response(
                '[{"id":"home-1","name":"Main Residence"}]',
                200,
              );
            }
            if (request.method == 'POST' &&
                request.url.path == '/api/homes/home-1/pairing-codes') {
              pairingRequest = request;
              return http.Response(
                '{"code":"ABC-234","home_id":"home-1",'
                '"expires_at":"2026-10-18T12:05:00Z","ttl_seconds":299}',
                201,
              );
            }
            return http.Response('Not Found', 404);
          }),
        );
        final provider = HomeProvider(apiClient: apiClient);
        await provider.fetchHomes('test-homeowner-session');

        final result = await provider.generatePairingCode(
          'test-homeowner-session',
          'home-1',
        );

        expect(result, isA<PairingCode>());
        expect(result.code, 'ABC-234');
        expect(result.homeId, 'home-1');
        expect(result.ttlSeconds, 299);
        expect(
          pairingRequest?.headers['authorization'],
          'Bearer test-homeowner-session',
        );
        expect(pairingRequest?.body, isEmpty);
      },
    );

    test(
      'does not request a pairing code without an authenticated session',
      () async {
        final provider = HomeProvider(
          apiClient: ApiClient(
            client: MockClient((_) async => http.Response('[]', 200)),
          ),
        );

        expect(
          provider.generatePairingCode(null, 'home-1'),
          throwsA(isA<ApiException>()),
        );
      },
    );
  });
}
