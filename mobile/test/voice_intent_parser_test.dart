import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/voice/services/voice_intent_parser.dart';

void main() {
  const parser = VoiceIntentParser();

  group('light intents', () {
    test('recognizes English room and all-lights commands', () {
      expect(
        parser.parse('Turn on the bedroom light').type,
        VoiceIntentType.lightOn,
      );
      expect(
        parser.parse('Turn off the bedroom light').type,
        VoiceIntentType.lightOff,
      );
      expect(
        parser.parse('Turn on all lights').type,
        VoiceIntentType.allLightsOn,
      );
      expect(
        parser.parse('Turn off all lights').type,
        VoiceIntentType.allLightsOff,
      );
      expect(parser.parse('Turn on the bedroom light').roomName, 'bedroom');
    });

    test('recognizes Roman Urdu commands', () {
      expect(
        parser.parse('Bedroom ki light on karo').type,
        VoiceIntentType.lightOn,
      );
      expect(
        parser.parse('Bedroom ki light band karo').type,
        VoiceIntentType.lightOff,
      );
      expect(
        parser.parse('Sab lights on kar do').type,
        VoiceIntentType.allLightsOn,
      );
      expect(
        parser.parse('Sab lights band kar do').type,
        VoiceIntentType.allLightsOff,
      );
    });

    test('recognizes Urdu-script commands', () {
      expect(
        parser.parse('بیڈروم کی لائٹ آن کرو').type,
        VoiceIntentType.lightOn,
      );
      expect(
        parser.parse('بیڈروم کی لائٹ بند کرو').type,
        VoiceIntentType.lightOff,
      );
      expect(
        parser.parse('سارے کمرے کی لائٹس آن کرو؟').type,
        VoiceIntentType.allLightsOn,
      );
      expect(
        parser.parse('تمام لائٹس بند کر دو۔').type,
        VoiceIntentType.allLightsOff,
      );
    });
  });

  group('safe rejection', () {
    test('rejects missing, unknown, and multiple rooms', () {
      expect(
        parser.parse('Turn on the lights').type,
        VoiceIntentType.ambiguous,
      );
      expect(
        parser.parse('Turn on the attic light').type,
        VoiceIntentType.unknown,
      );
      expect(
        parser.parse('Turn on the bedroom and kitchen lights').type,
        VoiceIntentType.ambiguous,
      );
      expect(
        parser.parse('Turn on the kitchenette light').type,
        VoiceIntentType.unknown,
      );
      expect(
        parser.parse('Turn on the officework light').type,
        VoiceIntentType.unknown,
      );
      expect(
        parser.parse('Turn on the flight light').type,
        VoiceIntentType.unknown,
      );
      expect(
        parser.parse('Turn on the living room and lounge lights').type,
        VoiceIntentType.ambiguous,
      );
    });

    test('rejects conflicting and unsafe commands', () {
      expect(
        parser.parse('Turn on and turn off the bedroom light').type,
        VoiceIntentType.ambiguous,
      );
      expect(parser.parse('Turn on the door').type, VoiceIntentType.unknown);
      expect(
        parser.parse('Turn on the lights and unlock the door').type,
        VoiceIntentType.ambiguous,
      );
    });
  });

  test('preserves safe informational intents deterministically', () {
    expect(parser.parse('hello').type, VoiceIntentType.greeting);
    expect(
      parser.parse('show security status').type,
      VoiceIntentType.securityStatus,
    );
    expect(
      parser.parse('read recent alerts').type,
      VoiceIntentType.recentAlerts,
    );
    expect(parser.parse('recent alerts').type, VoiceIntentType.recentAlerts);
    expect(parser.parse('help').type, VoiceIntentType.help);
    expect(parser.parse('help with lights').type, VoiceIntentType.help);
    expect(
      parser.parse('show light status').type,
      VoiceIntentType.securityStatus,
    );
  });
}
