class FaceRecordModel {
  final String id;
  final String memberId;
  final String? imagePath;
  final List<dynamic>? embedding;
  final int sampleCount;
  final DateTime createdAt;

  const FaceRecordModel({
    required this.id,
    required this.memberId,
    this.imagePath,
    this.embedding,
    this.sampleCount = 1,
    required this.createdAt,
  });

  factory FaceRecordModel.fromJson(Map<String, dynamic> json) {
    return FaceRecordModel(
      id: json['id']?.toString() ?? '',
      memberId: json['member_id']?.toString() ?? '',
      imagePath: json['image_path']?.toString(),
      embedding: json['embedding'] is List ? json['embedding'] as List : null,
      sampleCount: json['sample_count'] is int ? json['sample_count'] : 1,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'member_id': memberId,
      'image_path': imagePath,
      'embedding': embedding,
      'sample_count': sampleCount,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
