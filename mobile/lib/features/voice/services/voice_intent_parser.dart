enum VoiceIntentType {
  greeting,
  help,
  securityStatus,
  recentAlerts,
  lightOn,
  lightOff,
  allLightsOn,
  allLightsOff,
  unknown,
  ambiguous,
}

enum VoiceMatchQuality { exact, recognizedAlias, ambiguous, unknown }

class VoiceIntent {
  const VoiceIntent(
    this.type,
    this.message, {
    this.roomName,
    this.matchQuality = VoiceMatchQuality.unknown,
  });

  final VoiceIntentType type;
  final String message;
  final String? roomName;
  final VoiceMatchQuality matchQuality;
}

class VoiceIntentParser {
  const VoiceIntentParser();

  static const _roomAliases = <String, String>{
    'bedroom': 'bedroom',
    'بیڈروم': 'bedroom',
    'kitchen': 'kitchen',
    'کچن': 'kitchen',
    'living room': 'living room',
    'lounge': 'living room',
    'لاؤنج': 'living room',
    'bathroom': 'bathroom',
    'bath room': 'bathroom',
    'باتھ روم': 'bathroom',
    'dining room': 'dining room',
    'ڈائننگ روم': 'dining room',
    'office': 'office',
    'دفتر': 'office',
    'study': 'study',
    'garage': 'garage',
  };

  VoiceIntent parse(String transcript) {
    final text = _normalize(transcript);
    final tokens = _tokens(text);
    if (tokens.isEmpty) {
      return const VoiceIntent(
        VoiceIntentType.unknown,
        'No command detected.',
        matchQuality: VoiceMatchQuality.unknown,
      );
    }
    if (_containsDoorCommand(tokens)) {
      final hasLightLanguage = _containsLightLanguage(tokens);
      return VoiceIntent(
        hasLightLanguage ? VoiceIntentType.ambiguous : VoiceIntentType.unknown,
        hasLightLanguage
            ? 'That mixes a light command with an unsupported door command.'
            : 'Door commands are not enabled.',
        matchQuality: hasLightLanguage
            ? VoiceMatchQuality.ambiguous
            : VoiceMatchQuality.unknown,
      );
    }

    // Preserve the existing informational-intent priority before light parsing.
    if (_containsToken(tokens, {'hello', 'hi', 'salam', 'assalam'})) {
      return const VoiceIntent(
        VoiceIntentType.greeting,
        'Hello.',
        matchQuality: VoiceMatchQuality.exact,
      );
    }
    if (_containsToken(tokens, {'help', 'madad'})) {
      return const VoiceIntent(
        VoiceIntentType.help,
        'You can ask for security status or recent alerts.',
        matchQuality: VoiceMatchQuality.recognizedAlias,
      );
    }
    if (_containsToken(tokens, {'security', 'status'})) {
      return const VoiceIntent(
        VoiceIntentType.securityStatus,
        'Security status is available on the dashboard.',
        matchQuality: VoiceMatchQuality.recognizedAlias,
      );
    }
    if (_containsToken(tokens, {
      'alert',
      'alerts',
      'notification',
      'notifications',
    })) {
      return const VoiceIntent(
        VoiceIntentType.recentAlerts,
        'Recent alerts are available on the dashboard.',
        matchQuality: VoiceMatchQuality.recognizedAlias,
      );
    }

    final lightIntent = _parseLightCommand(text, tokens);
    if (lightIntent != null) return lightIntent;

    return const VoiceIntent(
      VoiceIntentType.unknown,
      'That command is not enabled yet.',
      matchQuality: VoiceMatchQuality.unknown,
    );
  }

  VoiceIntent? _parseLightCommand(String text, List<String> tokens) {
    if (!_containsLightLanguage(tokens)) return null;

    final wantsOn = _containsOnAction(tokens);
    final wantsOff = _containsOffAction(tokens);
    if (wantsOn && wantsOff) {
      return const VoiceIntent(
        VoiceIntentType.ambiguous,
        'The command contains conflicting light actions.',
        matchQuality: VoiceMatchQuality.ambiguous,
      );
    }
    if (!wantsOn && !wantsOff) {
      return const VoiceIntent(
        VoiceIntentType.ambiguous,
        'Say whether you want the lights on or off.',
        matchQuality: VoiceMatchQuality.ambiguous,
      );
    }

    final roomMentions = _findRoomMentions(tokens);
    final allLights = _containsAllLightsCommand(tokens);
    if (roomMentions.length > 1 || (allLights && roomMentions.isNotEmpty)) {
      return const VoiceIntent(
        VoiceIntentType.ambiguous,
        'Specify one room or choose all lights, not both.',
        matchQuality: VoiceMatchQuality.ambiguous,
      );
    }
    if (!allLights && roomMentions.isEmpty) {
      final missingRoom = _hasGenericLightTarget(tokens);
      return VoiceIntent(
        missingRoom ? VoiceIntentType.ambiguous : VoiceIntentType.unknown,
        missingRoom
            ? 'Specify one room for the light command.'
            : 'That room is not supported.',
        matchQuality: missingRoom
            ? VoiceMatchQuality.ambiguous
            : VoiceMatchQuality.unknown,
      );
    }

    final type = allLights
        ? (wantsOn ? VoiceIntentType.allLightsOn : VoiceIntentType.allLightsOff)
        : (wantsOn ? VoiceIntentType.lightOn : VoiceIntentType.lightOff);
    final roomName = allLights ? null : roomMentions.single;
    return VoiceIntent(
      type,
      allLights
          ? (wantsOn ? 'All lights requested on.' : 'All lights requested off.')
          : (wantsOn
                ? 'The $roomName light was requested on.'
                : 'The $roomName light was requested off.'),
      roomName: roomName,
      matchQuality: _isCanonicalEnglish(text)
          ? VoiceMatchQuality.exact
          : VoiceMatchQuality.recognizedAlias,
    );
  }

  String _normalize(String value) => value
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[.!?,;:،؛؟۔]+'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ');

  List<String> _tokens(String text) =>
      text.split(' ').where((token) => token.isNotEmpty).toList();

  bool _containsToken(List<String> tokens, Set<String> values) =>
      tokens.any(values.contains);

  bool _containsLightLanguage(List<String> tokens) =>
      _containsToken(tokens, {'light', 'lights', 'لائٹ', 'لائٹس'});

  bool _containsOnAction(List<String> tokens) => _containsAnyPhrase(tokens, [
    ['turn', 'on'],
    ['switch', 'on'],
    ['light', 'on'],
    ['lights', 'on'],
    ['on', 'karo'],
    ['on', 'kar', 'do'],
    ['jala', 'do'],
    ['آن'],
    ['چلا', 'دو'],
  ]);

  bool _containsOffAction(List<String> tokens) => _containsAnyPhrase(tokens, [
    ['turn', 'off'],
    ['switch', 'off'],
    ['light', 'off'],
    ['lights', 'off'],
    ['band', 'karo'],
    ['band', 'kar', 'do'],
    ['بند'],
    ['بجھا', 'دو'],
  ]);

  bool _containsAllLightsCommand(List<String> tokens) =>
      _containsAnyPhrase(tokens, [
        ['all', 'light'],
        ['all', 'lights'],
        ['sab', 'light'],
        ['sab', 'lights'],
        ['tamam', 'light'],
        ['tamam', 'lights'],
        ['سارے', 'کمرے', 'کی', 'لائٹس'],
        ['تمام', 'لائٹس'],
      ]);

  bool _containsDoorCommand(List<String> tokens) =>
      _containsToken(tokens, {'door', 'unlock', 'lock', 'دروازہ', 'تالا'});

  bool _containsAnyPhrase(List<String> tokens, List<List<String>> phrases) =>
      phrases.any((phrase) => _containsPhrase(tokens, phrase));

  bool _containsPhrase(List<String> tokens, List<String> phrase) {
    if (phrase.length > tokens.length) return false;
    for (var start = 0; start <= tokens.length - phrase.length; start++) {
      var matches = true;
      for (var offset = 0; offset < phrase.length; offset++) {
        if (tokens[start + offset] != phrase[offset]) {
          matches = false;
          break;
        }
      }
      if (matches) return true;
    }
    return false;
  }

  List<String> _findRoomMentions(List<String> tokens) {
    final mentions = <String>[];
    for (var start = 0; start < tokens.length; start++) {
      for (final entry in _roomAliases.entries) {
        final aliasTokens = entry.key.split(' ');
        if (_matchesAt(tokens, start, aliasTokens)) {
          mentions.add(entry.value);
        }
      }
    }
    return mentions;
  }

  bool _matchesAt(List<String> tokens, int start, List<String> phrase) {
    if (start + phrase.length > tokens.length) return false;
    for (var offset = 0; offset < phrase.length; offset++) {
      if (tokens[start + offset] != phrase[offset]) return false;
    }
    return true;
  }

  bool _hasGenericLightTarget(List<String> tokens) {
    for (var index = 0; index < tokens.length; index++) {
      if (!_containsLightLanguage([tokens[index]])) continue;
      if (index == 0) return true;
      final previous = tokens[index - 1];
      if (previous == 'the' || previous == 'on' || previous == 'off') {
        return true;
      }
    }
    return false;
  }

  bool _isCanonicalEnglish(String text) =>
      RegExp(r'^(turn|switch) (on|off) the .+ light$').hasMatch(text) ||
      RegExp(r'^(turn|switch) (on|off) all lights$').hasMatch(text);
}
