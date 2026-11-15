class VoiceCommandModel {
  const VoiceCommandModel({
    required this.id,
    required this.homeId,
    required this.command,
    required this.targetType,
    required this.status,
    this.roomId,
    this.expiresAt,
    this.terminalAt,
    this.resolvedAt,
  });

  final String id;
  final String homeId;
  final String command;
  final String targetType;
  final String status;
  final String? roomId;
  final DateTime? expiresAt;
  final DateTime? terminalAt;
  final DateTime? resolvedAt;

  factory VoiceCommandModel.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final homeId = json['home_id'];
    final command = json['command'];
    final targetType = json['target_type'];
    final status = json['status'];
    if ([
      id,
      homeId,
      command,
      targetType,
      status,
    ].any((value) => value is! String)) {
      throw const FormatException('Invalid voice command response.');
    }
    DateTime? parseDate(dynamic value) =>
        value is String ? DateTime.tryParse(value) : null;
    return VoiceCommandModel(
      id: id as String,
      homeId: homeId as String,
      command: command as String,
      targetType: targetType as String,
      status: status as String,
      roomId: json['room_id'] as String?,
      expiresAt: parseDate(json['expires_at']),
      terminalAt: parseDate(json['terminal_at']),
      resolvedAt: parseDate(json['resolved_at']),
    );
  }
}

class VoiceCommandSubmission {
  const VoiceCommandSubmission({
    required this.command,
    required this.existing,
    required this.deviceCount,
  });

  final VoiceCommandModel command;
  final bool existing;
  final int deviceCount;

  factory VoiceCommandSubmission.fromJson(Map<String, dynamic> json) {
    final commandJson = json['command'];
    final existing = json['existing'];
    final deviceCount = json['device_count'];
    if (commandJson is! Map || existing is! bool || deviceCount is! int) {
      throw const FormatException('Invalid voice command acceptance response.');
    }
    return VoiceCommandSubmission(
      command: VoiceCommandModel.fromJson(
        Map<String, dynamic>.from(commandJson),
      ),
      existing: existing,
      deviceCount: deviceCount,
    );
  }
}
