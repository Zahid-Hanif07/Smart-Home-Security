import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' hide LocalStorage;
import 'package:mobile/app/theme/app_theme.dart';
import 'package:mobile/features/home/presentation/home_screen.dart';
import 'package:mobile/features/home/provider/alerts_provider.dart';
import 'package:mobile/features/home/provider/camera_stream_provider.dart';
import 'package:mobile/features/home/provider/face_occlusion_provider.dart';
import 'package:mobile/features/home/widgets/security_status_card.dart';
import 'package:mobile/features/home/widgets/recent_activity.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/features/voice/provider/voice_provider.dart';
import 'package:mobile/features/voice/services/android_audio_recorder.dart';
import 'package:mobile/features/voice/services/offline_whisper_service.dart';
import 'package:mobile/models/security_log_model.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

class _TestVoiceRecorder implements VoiceRecorder {
  @override
  Future<bool> start() async => true;

  @override
  Future<String?> stop() async => '/cache/voice.wav';

  @override
  Future<void> cancel() async {}
}

class _TestSpeechRecognizer implements SpeechRecognitionService {
  @override
  Future<String> transcribe(String path, {required String language}) async =>
      'show security status';
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

  group('HomeScreen & Dashboard Widget Tests', () {
    testWidgets('1. SecurityStatusCard renders secure state', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: SecurityStatusCard(
              homeName: 'Main Residence',
              status: SecurityStatusState.secure,
            ),
          ),
        ),
      );

      expect(find.text('Your home is protected'), findsOneWidget);
      expect(find.text('SECURE'), findsOneWidget);
    });

    testWidgets('2. RecentActivity renders empty state when no logs exist', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: RecentActivity(
              events: [],
              isLoading: false,
              isConnected: true,
            ),
          ),
        ),
      );

      expect(find.text('Recent activity'), findsOneWidget);
      expect(find.text('No recent activity'), findsOneWidget);
      expect(
        find.text('Your home security events will appear here.'),
        findsOneWidget,
      );
    });

    testWidgets('3. RecentActivity renders event items when logs exist', (
      WidgetTester tester,
    ) async {
      final sampleLogs = [
        SecurityLogModel(
          id: 'log-1',
          homeId: 'home-1',
          eventType: 'unknown_person',
          description: 'Unrecognized individual',
          createdAt: DateTime(2026, 9, 30, 21, 0),
        ),
        SecurityLogModel(
          id: 'log-2',
          homeId: 'home-1',
          eventType: 'authorized_person',
          personName: 'Zahid',
          isAuthorized: true,
          createdAt: DateTime(2026, 9, 30, 20, 30),
        ),
      ];

      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme,
          home: Scaffold(
            body: RecentActivity(
              events: sampleLogs,
              isLoading: false,
              isConnected: true,
            ),
          ),
        ),
      );

      expect(find.text('Recent activity'), findsOneWidget);
      expect(find.text('Unknown person detected'), findsOneWidget);
      expect(find.text('Zahid recognized'), findsOneWidget);
    });

    testWidgets('4. Full HomeScreen renders dashboard layout', (
      WidgetTester tester,
    ) async {
      final authProvider = AuthProvider();
      final homeProvider = HomeProvider();
      final membersProvider = MembersProvider();
      final voiceProvider = VoiceProvider(
        recorder: _TestVoiceRecorder(),
        recognizer: _TestSpeechRecognizer(),
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
            ChangeNotifierProvider<HomeProvider>.value(value: homeProvider),
            ChangeNotifierProvider<MembersProvider>.value(
              value: membersProvider,
            ),
            ChangeNotifierProvider<AlertsProvider>(
              create: (_) => AlertsProvider(),
            ),
            ChangeNotifierProvider<CameraStreamProvider>(
              create: (_) => CameraStreamProvider(),
            ),
            ChangeNotifierProvider<FaceOcclusionProvider>(
              create: (_) => FaceOcclusionProvider(),
            ),
            ChangeNotifierProvider<VoiceProvider>.value(value: voiceProvider),
          ],
          child: MaterialApp(
            theme: AppTheme.lightTheme,
            home: const HomeScreen(),
          ),
        ),
      );

      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.text('Live camera'), findsOneWidget);
      expect(find.text('Pair Camera'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Recent activity'),
        400,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('Recent activity'), findsOneWidget);
      expect(find.text('Face analysis'), findsOneWidget);
      expect(find.text('Voice control'), findsOneWidget);
      expect(find.text('Home'), findsOneWidget);
      expect(find.text('People'), findsOneWidget);
      expect(find.text('Homes'), findsOneWidget);
      expect(find.text('Alerts'), findsOneWidget);
    });
  });
}
