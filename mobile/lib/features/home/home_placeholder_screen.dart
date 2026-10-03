import 'package:flutter/material.dart';
import 'package:mobile/features/home/presentation/home_screen.dart';

export 'presentation/home_screen.dart';

/// Legacy alias for HomeScreen to preserve route compatibility
class HomePlaceholderScreen extends StatelessWidget {
  const HomePlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const HomeScreen();
  }
}
