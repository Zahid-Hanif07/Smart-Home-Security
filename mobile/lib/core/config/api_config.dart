import 'package:flutter/foundation.dart';

class ApiConfig {
  // Default Base URL for Android Emulator vs Local Desktop / Web
  static const String androidEmulatorUrl = 'http://10.0.2.2:8085';
  static const String localhostUrl = 'http://127.0.0.1:8085';

  // Supabase Configuration
  static const String supabaseUrl = 'https://fbwbgcaviawlqigemrdg.supabase.co';
  static const String supabaseAnonKey = 'sb_publishable_hLZSHbWwOCq2HReqf6hW1A_PciCVbFf';

  static String? _customBaseUrl;

  static void setCustomBaseUrl(String url) {
    _customBaseUrl = url.endsWith('/') ? url.substring(0, url.length - 1) : url;
  }

  static String get baseUrl {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) {
      return _customBaseUrl!;
    }

    if (kIsWeb) {
      return localhostUrl;
    }

    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return androidEmulatorUrl;
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
