import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/home/provider/camera_stream_provider.dart';

void main() {
  test('debug video status keeps only the three safe status fields', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/video/status');
      return http.Response(
        '{"publisher_connected":true,"home_id_match":true,"reason":"streaming"}',
        200,
      );
    });
    final provider = CameraStreamProvider(apiClient: ApiClient(client: client));

    await provider.debugCheckVideoStatus('home-id', 'access-token');

    expect(
      provider.debugVideoStatusMessage,
      'publisher_connected: true\nhome_id_match: true\nreason: streaming',
    );
    provider.dispose();
  });

  test('debug video status rejects missing credentials without a request', () async {
    var requestMade = false;
    final client = MockClient((request) async {
      requestMade = true;
      return http.Response('{}', 200);
    });
    final provider = CameraStreamProvider(apiClient: ApiClient(client: client));

    await provider.debugCheckVideoStatus(null, 'access-token');

    expect(requestMade, isFalse);
    expect(provider.debugVideoStatusMessage, 'Video status unavailable');
    provider.dispose();
  });

  test('debug video status rejects unexpected response shapes safely', () async {
    final client = MockClient((request) async {
      return http.Response('{"reason":"private detail"}', 200);
    });
    final provider = CameraStreamProvider(apiClient: ApiClient(client: client));

    await provider.debugCheckVideoStatus('home-id', 'access-token');

    expect(provider.debugVideoStatusMessage, 'Video status unavailable');
    provider.dispose();
  });

  test('debug video status hides HTTP error details', () async {
    final client = MockClient((request) async {
      return http.Response('{"detail":"private server detail"}', 401);
    });
    final provider = CameraStreamProvider(apiClient: ApiClient(client: client));

    await provider.debugCheckVideoStatus('home-id', 'access-token');

    expect(provider.debugVideoStatusMessage, 'Video status unavailable');
    provider.dispose();
  });
}
