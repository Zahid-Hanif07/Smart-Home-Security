class SecurityLogModel {
  final String id;
  final String homeId;
  final String? deviceId;
  final String eventType;
  final String? description;
  final String? personName;
  final bool? isAuthorized;
  final String? imagePath;
  final DateTime createdAt;

  SecurityLogModel({
    required this.id,
    required this.homeId,
    this.deviceId,
    required this.eventType,
    this.description,
    this.personName,
    this.isAuthorized,
    this.imagePath,
    required this.createdAt,
  });

  factory SecurityLogModel.fromJson(Map<String, dynamic> json) {
    return SecurityLogModel(
      id: json['id']?.toString() ?? '',
      homeId: json['home_id']?.toString() ?? '',
      deviceId: json['device_id']?.toString(),
      eventType: json['event_type']?.toString() ?? 'unknown',
      description: json['description']?.toString(),
      personName: json['person_name']?.toString(),
      isAuthorized: json['is_authorized'] as bool?,
      imagePath: json['image_path']?.toString(),
      createdAt: json['created_at'] != null
          ? (DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now())
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'home_id': homeId,
      'device_id': deviceId,
      'event_type': eventType,
      'description': description,
      'person_name': personName,
      'is_authorized': isAuthorized,
      'image_path': imagePath,
      'created_at': createdAt.toIso8601String(),
    };
  }

  /// Human-readable title for UI
  String get displayTitle {
    if (personName != null && personName!.isNotEmpty) {
      if (isAuthorized == true) {
        return '$personName recognized';
      } else if (isAuthorized == false) {
        return 'Unrecognized person ($personName)';
      } else {
        return 'Person detected: $personName';
      }
    }

    final typeLower = eventType.toLowerCase();
    if (typeLower == 'unknown_person') {
      return 'Unknown person detected';
    } else if (typeLower == 'authorized_person') {
      return 'Authorized person recognized';
    } else if (typeLower == 'motion_detected') {
      return 'Motion detected';
    } else {
      return eventType.replaceAll('_', ' ');
    }
  }
}
