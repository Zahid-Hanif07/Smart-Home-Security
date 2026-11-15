import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/home/provider/face_occlusion_provider.dart';

void main() {
  FaceOcclusionProvider providerFor(
    Future<http.Response> Function(http.Request) handler, {
    Duration interval = const Duration(hours: 1),
  }) {
    return FaceOcclusionProvider(
      apiClient: ApiClient(client: MockClient(handler)),
      pollingInterval: interval,
    );
  }

  test('loads a successful FaceOcc response through homeowner GET', () async {
    final provider = providerFor((request) async {
      expect(request.url.path, ApiConfig.faceOcclusionStatusEndpoint);
      expect(request.url.queryParameters['home_id'], 'home-1');
      expect(request.headers['authorization'], 'Bearer token');
      return http.Response(
        '{"home_id":"home-1","results":[{"face_index":0,"frame_sequence":4,"status":"success","visible_ratio":0.75,"inference_ms":12.5,"result_timestamp":"2026-01-01T00:00:00Z","freshness":"fresh","reason":"segmentation_completed"}]}',
        200,
      );
    });
    addTearDown(provider.dispose);

    provider.startPolling('home-1', 'token');
    await Future<void>.delayed(Duration.zero);

    expect(provider.state, FaceOcclusionViewState.analyzed);
    expect(provider.results.single.visibleRatio, 0.75);
  });

  test('empty, stale, no-face and unknown statuses are safe', () async {
    final responses = <String>[
      '{"home_id":"home-1","results":[]}',
      '{"home_id":"home-1","results":[{"face_index":0,"frame_sequence":4,"status":"success","freshness":"stale","reason":"old"}]}',
      '{"home_id":"home-1","results":[{"face_index":-1,"frame_sequence":4,"status":"no_face","freshness":"fresh","reason":"no_face_detected"}]}',
      '{"home_id":"home-1","results":[{"face_index":0,"frame_sequence":4,"status":"future_status","freshness":"fresh","reason":"future"}]}',
    ];
    final provider = providerFor((_) async => http.Response(responses.removeAt(0), 200));
    addTearDown(provider.dispose);

    provider.startPolling('home-1', 'token');
    await Future<void>.delayed(Duration.zero);
    expect(provider.state, FaceOcclusionViewState.waiting);

    await provider.refresh('home-1', 'token');
    expect(provider.state, FaceOcclusionViewState.stale);
    await provider.refresh('home-1', 'token');
    expect(provider.state, FaceOcclusionViewState.noFace);
    await provider.refresh('home-1', 'token');
    expect(provider.state, FaceOcclusionViewState.uncertain);
  });

  test('maps unauthorized and network errors without exposing response details', () async {
    final unauthorized = providerFor(
      (_) async => http.Response('{"detail":"private backend detail"}', 401),
    );
    addTearDown(unauthorized.dispose);
    unauthorized.startPolling('home-1', 'token');
    await Future<void>.delayed(Duration.zero);
    expect(unauthorized.state, FaceOcclusionViewState.error);
    expect(unauthorized.errorMessage, 'Face analysis requires sign-in.');
    expect(unauthorized.errorMessage, isNot(contains('private')));
  });

  test('discards a response for a different home', () async {
    final provider = providerFor((_) async => http.Response(
          '{"home_id":"other-home","results":[{"face_index":0,"frame_sequence":4,"status":"success","freshness":"fresh","reason":"segmentation_completed"}]}',
          200,
        ));
    addTearDown(provider.dispose);

    provider.startPolling('home-1', 'token');
    await Future<void>.delayed(Duration.zero);

    expect(provider.results, isEmpty);
    expect(provider.state, FaceOcclusionViewState.error);
    expect(provider.errorMessage, 'Face analysis is unavailable.');
  });

  test('missing response home id is treated as unavailable', () async {
    final provider = providerFor((_) async => http.Response(
          '{"results":[{"face_index":0,"frame_sequence":4,"status":"success","freshness":"fresh","reason":"segmentation_completed"}]}',
          200,
        ));
    addTearDown(provider.dispose);

    provider.startPolling('home-1', 'token');
    await Future<void>.delayed(Duration.zero);

    expect(provider.results, isEmpty);
    expect(provider.state, FaceOcclusionViewState.error);
  });

  test('home switching clears old results and avoids duplicate timers', () async {
    var calls = 0;
    final provider = providerFor((request) async {
      calls++;
      return http.Response('{"home_id":"${request.url.queryParameters['home_id']}","results":[]}', 200);
    }, interval: const Duration(milliseconds: 20));
    addTearDown(provider.dispose);

    provider.startPolling('home-1', 'token');
    provider.startPolling('home-1', 'token');
    await Future<void>.delayed(const Duration(milliseconds: 5));
    expect(provider.results, isEmpty);
    provider.startPolling('home-2', 'token');
    expect(provider.results, isEmpty);
    await Future<void>.delayed(const Duration(milliseconds: 55));
    expect(calls, lessThanOrEqualTo(4));
  });

  test('stopPolling halts future requests', () async {
    var calls = 0;
    final provider = providerFor((_) async {
      calls++;
      return http.Response('{"home_id":"home-1","results":[]}', 200);
    }, interval: const Duration(milliseconds: 10));
    provider.startPolling('home-1', 'token');
    await Future<void>.delayed(const Duration(milliseconds: 15));
    provider.stopPolling();
    final stoppedAt = calls;
    await Future<void>.delayed(const Duration(milliseconds: 35));
    expect(calls, stoppedAt);
    provider.dispose();
  });
}
