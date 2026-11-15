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

    test(
      'video status request preserves home_id and uses homeowner Bearer auth',
      () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'GET');
          expect(request.url.path, ApiConfig.videoStatusEndpoint);
          expect(request.url.queryParameters, {'home_id': 'home-123'});
          expect(request.headers['authorization'], 'Bearer test-access-token');
          return http.Response('{"reason":"streaming"}', 200);
        });

        final apiClient = ApiClient(client: mockClient);
        final result = await apiClient.getVideoStatus(
          'home-123',
          'test-access-token',
        );

        expect(result, {'reason': 'streaming'});
      },
    );

    test('4. API Exception status code mapping', () {
      final exc401 = ApiException.fromStatusCode(401, {
        'detail': 'Invalid token',
      });
      expect(exc401.statusCode, equals(401));
      expect(exc401.message, contains('Unauthorized access'));

      final exc403 = ApiException.fromStatusCode(403);
      expect(exc403.statusCode, equals(403));
      expect(exc403.message, contains("don't have permission"));
    });

    test(
      'voice command acceptance preserves existing and device count',
      () async {
        final mockClient = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/api/homes/home-123/commands');
          expect(request.headers['authorization'], 'Bearer token');
          return http.Response(
            '{"command":{"id":"cmd-1","home_id":"home-123","command":"all_lights_on","target_type":"all_lights","status":"accepted"},"existing":true,"device_count":2}',
            202,
          );
        });
        final result = await ApiClient(client: mockClient).createVoiceCommand(
          'home-123',
          'client-1',
          'all_lights_on',
          'all_lights',
          null,
          'token',
        );
        expect(result.existing, isTrue);
        expect(result.deviceCount, 2);
        expect(result.command.id, 'cmd-1');
      },
    );

    test('voice command status retrieves the direct command response', () async {
      final mockClient = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/homes/home-123/commands/cmd-1');
        return http.Response(
          '{"id":"cmd-1","home_id":"home-123","command":"all_lights_on","target_type":"all_lights","status":"acknowledged"}',
          200,
        );
      });
      final result = await ApiClient(
        client: mockClient,
      ).getVoiceCommand('home-123', 'cmd-1', 'token');
      expect(result.status, 'acknowledged');
    });

    test('room list returns canonical room IDs', () async {
      final mockClient = MockClient((request) async {
        expect(request.url.path, '/api/homes/home-123/rooms');
        return http.Response(
          '{"rooms":[{"id":"room-1","name":"Living Room"}]}',
          200,
        );
      });
      final rooms = await ApiClient(
        client: mockClient,
      ).getHomeRooms('home-123', 'token');
      expect(rooms.single.id, 'room-1');
      expect(rooms.single.name, 'Living Room');
    });
  });
}
