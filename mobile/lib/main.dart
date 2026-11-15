// import 'package:flutter/material.dart';
// import 'package:supabase_flutter/supabase_flutter.dart';
// import 'package:mobile/core/config/api_config.dart';
// import 'package:mobile/app/app.dart';

// void main() async {
//   WidgetsFlutterBinding.ensureInitialized();
//   await Supabase.initialize(
//     url: ApiConfig.supabaseUrl,
//     publishableKey: ApiConfig.supabaseAnonKey,
//   );
//   runApp(const SmartHomeApp());
// }
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/app/app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  debugPrint('OTTO_STARTUP_1: Flutter initialized');

  try {
    debugPrint('OTTO_STARTUP_2: Supabase initialization started');

    await Supabase.initialize(
      url: ApiConfig.supabaseUrl,
      publishableKey: ApiConfig.supabaseAnonKey,
    ).timeout(const Duration(seconds: 20));

    debugPrint('OTTO_STARTUP_3: Supabase initialization completed');
  } catch (e, stackTrace) {
    debugPrint('OTTO_STARTUP_ERROR: $e');
    debugPrint('$stackTrace');
  }

  debugPrint('OTTO_STARTUP_4: Calling runApp');
  runApp(const SmartHomeApp());
}
