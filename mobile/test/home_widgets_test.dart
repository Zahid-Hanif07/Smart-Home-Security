import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_theme.dart';
import 'package:mobile/features/home/presentation/home_screen.dart';
import 'package:mobile/features/home/widgets/security_status_card.dart';
import 'package:mobile/features/home/widgets/recent_activity.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/models/security_log_model.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

void main() {
  group('HomeScreen & Dashboard Widget Tests', () {
    testWidgets('1. SecurityStatusCard renders secure state', (WidgetTester tester) async {
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

      expect(find.text('System Protected'), findsOneWidget);
      expect(find.text('SECURE'), findsOneWidget);
    });

    testWidgets('2. RecentActivity renders empty state when no logs exist', (WidgetTester tester) async {
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

      expect(find.text('Recent Activity'), findsOneWidget);
      expect(find.text('No recent security activity'), findsOneWidget);
      expect(find.text('Your home security events will appear here.'), findsOneWidget);
    });

    testWidgets('3. RecentActivity renders event items when logs exist', (WidgetTester tester) async {
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

      expect(find.text('Recent Activity'), findsOneWidget);
      expect(find.text('Unknown person detected'), findsOneWidget);
      expect(find.text('Zahid recognized'), findsOneWidget);
    });

    testWidgets('4. Full HomeScreen renders dashboard layout', (WidgetTester tester) async {
      final authProvider = AuthProvider();
      final homeProvider = HomeProvider();
      final membersProvider = MembersProvider();

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
            ChangeNotifierProvider<HomeProvider>.value(value: homeProvider),
            ChangeNotifierProvider<MembersProvider>.value(value: membersProvider),
          ],
          child: MaterialApp(
            theme: AppTheme.lightTheme,
            home: const HomeScreen(),
          ),
        ),
      );

      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.text('Live Camera View'), findsOneWidget);
      expect(find.text('FastAPI Engine'), findsOneWidget);
      expect(find.text('Recent Activity'), findsOneWidget);
      expect(find.text('Family Members & Faces'), findsOneWidget);
      expect(find.text('Home'), findsOneWidget);
      expect(find.text('Members'), findsOneWidget);
      expect(find.text('Settings'), findsOneWidget);
    });
  });
}
