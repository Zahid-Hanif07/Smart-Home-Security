// import 'package:flutter_test/flutter_test.dart';
// import 'package:integration_test/integration_test.dart';
// import 'package:mobile/features/voice/services/offline_whisper_service.dart';

// void main() {
//   IntegrationTestWidgetsFlutterBinding.ensureInitialized();

//   testWidgets('Run real Whisper Tiny inference on Android', (tester) async {
//     final service = OfflineWhisperService();

//     try {
//       const audioPath =
//           '/data/user/0/com.example.mobile/files/voice_test/english.wav';

//       final transcript = await service.transcribe(
//         audioPath,
//         language: 'en',
//       );

//       print('ANDROID_WHISPER_TRANSCRIPT=$transcript');
//       expect(transcript, isNotEmpty);
//     } finally {
//       service.dispose();
//     }
//   });
// }

import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mobile/features/voice/services/offline_whisper_service.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('Run Whisper Tiny batch evaluation on Android', (tester) async {
    final service = OfflineWhisperService();

    const samples = <String, double>{
      '1675': 8.76,
      '1728': 5.76,
      '1806': 9.90,
      '1846': 11.04,
      '1876': 10.80,
      '1904': 10.56,
      '1914': 6.96,
      '1938': 11.42,
      '1950': 11.46,
      '1972': 4.32,
    };

    final totalWatch = Stopwatch()..start();

    try {
      for (final entry in samples.entries) {
        final id = entry.key;
        final audioDuration = entry.value;
        final audioPath =
            '/data/user/0/com.example.mobile/files/voice_test/batch/en_$id.wav';

        final watch = Stopwatch()..start();

        final transcript = await service.transcribe(audioPath, language: 'en');

        watch.stop();

        final elapsedSeconds = watch.elapsedMilliseconds / 1000;
        final rtf = elapsedSeconds / audioDuration;

        print(
          'ANDROID_WHISPER_RESULT|$id|'
          '${audioDuration.toStringAsFixed(2)}|'
          '${watch.elapsedMilliseconds}|'
          '${rtf.toStringAsFixed(4)}|'
          '$transcript',
        );

        expect(
          transcript,
          isNotEmpty,
          reason: 'Sample $id returned empty text',
        );
      }

      totalWatch.stop();

      print('ANDROID_WHISPER_TOTAL_MS=${totalWatch.elapsedMilliseconds}');
      print('ANDROID_WHISPER_SAMPLE_COUNT=${samples.length}');
    } finally {
      service.dispose();
    }
  });
}
