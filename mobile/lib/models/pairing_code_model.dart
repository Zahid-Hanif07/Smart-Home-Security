class PairingCode {
  final String code;
  final String homeId;
  final DateTime expiresAt;
  final int ttlSeconds;

  const PairingCode({
    required this.code,
    required this.homeId,
    required this.expiresAt,
    required this.ttlSeconds,
  });

  factory PairingCode.fromJson(Map<String, dynamic> json) {
    return PairingCode(
      code: json['code'] as String,
      homeId: json['home_id'] as String,
      expiresAt: DateTime.parse(json['expires_at'] as String),
      ttlSeconds: json['ttl_seconds'] as int,
    );
  }
}
