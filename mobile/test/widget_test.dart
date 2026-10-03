import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/app.dart';

void main() {
  testWidgets('1. App launches and renders splash screen title', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartHomeApp());
    expect(find.text('SMART HOME SECURITY'), findsOneWidget);
    expect(find.text('AI Security & Voice Assistant Mobile Engine'), findsOneWidget);
    await tester.pumpAndSettle(const Duration(seconds: 1));
  });
}

