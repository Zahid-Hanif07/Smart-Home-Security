class FaceOcclusionDiagnostic {
  final int faceIndex;
  final int frameSequence;
  final String status;
  final double? visibleRatio;
  final double? inferenceMs;
  final DateTime? resultTimestamp;
  final String freshness;
  final String reason;

  const FaceOcclusionDiagnostic({
    required this.faceIndex,
    required this.frameSequence,
    required this.status,
    required this.visibleRatio,
    required this.inferenceMs,
    required this.resultTimestamp,
    required this.freshness,
    required this.reason,
  });

  factory FaceOcclusionDiagnostic.fromJson(Map<String, dynamic> json) {
    return FaceOcclusionDiagnostic(
      faceIndex: _intValue(json['face_index'], fallback: -1),
      frameSequence: _intValue(json['frame_sequence']),
      status: json['status'] is String ? json['status'] as String : 'unknown',
      visibleRatio: _doubleValue(json['visible_ratio']),
      inferenceMs: _doubleValue(json['inference_ms']),
      resultTimestamp: json['result_timestamp'] is String
          ? DateTime.tryParse(json['result_timestamp'] as String)
          : null,
      freshness: json['freshness'] is String
          ? json['freshness'] as String
          : 'stale',
      reason: json['reason'] is String ? json['reason'] as String : '',
    );
  }

  bool get isFresh => freshness == 'fresh';
  bool get isStale => freshness == 'stale' || status == 'stale';

  static int _intValue(Object? value, {int fallback = 0}) =>
      value is int ? value : fallback;

  static double? _doubleValue(Object? value) => value is num
      ? (value.isFinite ? value.toDouble() : null)
      : null;
}

class FaceOcclusionStatusResponse {
  final String? homeId;
  final List<FaceOcclusionDiagnostic> results;

  const FaceOcclusionStatusResponse({required this.homeId, required this.results});

  factory FaceOcclusionStatusResponse.fromJson(Map<String, dynamic> json) {
    final rawResults = json['results'];
    if (rawResults is! List) {
      return FaceOcclusionStatusResponse(
        homeId: json['home_id'] is String ? json['home_id'] as String : null,
        results: const [],
      );
    }
    return FaceOcclusionStatusResponse(
      homeId: json['home_id'] is String ? json['home_id'] as String : null,
      results: rawResults
          .whereType<Map<String, dynamic>>()
          .map(FaceOcclusionDiagnostic.fromJson)
          .toList(growable: false),
    );
  }
}
