import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_theme.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/home/provider/face_occlusion_provider.dart';
import 'package:mobile/features/home/widgets/face_analysis_panel.dart';

void main() {
  testWidgets('renders analyzed metrics and stale state safely', (tester) async {
    final client = MockClient((_) async => http.Response(
          '{"home_id":"home-1","results":[{"face_index":0,"frame_sequence":1,"status":"success","visible_ratio":0.8,"inference_ms":15.0,"result_timestamp":"2026-01-01T00:00:00Z","freshness":"fresh","reason":"segmentation_completed"}]}',
          200,
        ));
    final provider = FaceOcclusionProvider(
      apiClient: ApiClient(client: client),
      pollingInterval: const Duration(hours: 1),
    );
    addTearDown(provider.dispose);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<FaceOcclusionProvider>.value(value: provider),
        ],
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(body: FaceAnalysisPanel()),
        ),
      ),
    );
    provider.startPolling('home-1', 'token');
    await tester.pump();

    expect(find.text('ANALYZED'), findsOneWidget);
    expect(find.textContaining('80.0% visible'), findsOneWidget);
    expect(find.textContaining('15.0 ms'), findsOneWidget);
    provider.stopPolling();
  });
}
