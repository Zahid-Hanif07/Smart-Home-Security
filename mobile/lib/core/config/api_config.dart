import 'package:flutter/foundation.dart';

/// Centralized API Configuration for OTTO Smart Home Security.
///
/// PHYSICAL ANDROID DEVICE TESTING:
/// Physical Android devices connect to FastAPI running on the laptop over Wi-Fi LAN.
/// Default Physical Android URL: http://192.168.0.103:8085
///
/// UPDATING THE LAPTOP IP ADDRESS:
/// 1. Run `ipconfig` on your laptop shell to find your current Wireless LAN IPv4 address.
/// 2. Either update [defaultPhysicalAndroidUrl] below, or build/run with:
///    `flutter run --dart-define=API_BASE_URL=http://<YOUR_IP>:8085`
/// 3. To explicitly target Android Emulator instead:
///    `flutter run --dart-define=USE_EMULATOR=true`
class ApiConfig {
  static const String defaultPhysicalAndroidUrl = 'http://192.168.0.103:8085';
  static const String androidEmulatorUrl = 'http://10.0.2.2:8085';
  static const String localhostUrl = 'http://127.0.0.1:8085';

  // Supabase Configuration
  static const String supabaseUrl = 'https://fbwbgcaviawlqigemrdg.supabase.co';
  static const String supabaseAnonKey = 'sb_publishable_hLZSHbWwOCq2HReqf6hW1A_PciCVbFf';

  static String? _customBaseUrl;

  /// Programmatically override base URL at runtime if needed
  static void setCustomBaseUrl(String url) {
    _customBaseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
  }

  /// Get active base URL according to target platform & build environment
  static String get baseUrl {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) {
      return _customBaseUrl!;
    }

    // Check for build-time environment variable override via --dart-define
    const envDefinedUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (envDefinedUrl.isNotEmpty) {
      return envDefinedUrl.endsWith('/')
          ? envDefinedUrl.substring(0, envDefinedUrl.length - 1)
          : envDefinedUrl;
    }

    const useEmulator = bool.fromEnvironment('USE_EMULATOR', defaultValue: false);
    if (useEmulator) {
      return androidEmulatorUrl;
    }

    if (kIsWeb) {
      return localhostUrl;
    }

    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return defaultPhysicalAndroidUrl;
      case TargetPlatform.iOS:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.linux:
      case TargetPlatform.fuchsia:
        return localhostUrl;
    }
  }

  // API Endpoints
  static const String healthEndpoint = '/health';
  static const String profileEndpoint = '/api/auth/me';
  static const String homesEndpoint = '/api/homes';
  static const String videoStreamEndpoint = '/video/stream';
  static const String videoStatusEndpoint = '/video/status';
}
