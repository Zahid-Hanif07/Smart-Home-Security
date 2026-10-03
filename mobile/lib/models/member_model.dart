class MemberModel {
  final String id;
  final String homeId;
  final String? userId;
  final String name;
  final String? relation;
  final bool isActive;
  final DateTime createdAt;
  final int faceCount;

  const MemberModel({
    required this.id,
    required this.homeId,
    this.userId,
    required this.name,
    this.relation,
    this.isActive = true,
    required this.createdAt,
    this.faceCount = 0,
  });

  factory MemberModel.fromJson(Map<String, dynamic> json) {
    return MemberModel(
      id: json['id']?.toString() ?? '',
      homeId: json['home_id']?.toString() ?? '',
      userId: json['user_id']?.toString(),
      name: json['name']?.toString() ?? 'Family Member',
      relation: json['relation']?.toString(),
      isActive: json['is_active'] ?? true,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      faceCount: json['face_count'] is int
          ? json['face_count']
          : (json['faces'] is List ? (json['faces'] as List).length : 0),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'home_id': homeId,
      'user_id': userId,
      'name': name,
      'relation': relation,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'face_count': faceCount,
    };
  }

  MemberModel copyWith({
    String? id,
    String? homeId,
    String? userId,
    String? name,
    String? relation,
    bool? isActive,
    DateTime? createdAt,
    int? faceCount,
  }) {
    return MemberModel(
      id: id ?? this.id,
      homeId: homeId ?? this.homeId,
      userId: userId ?? this.userId,
      name: name ?? this.name,
      relation: relation ?? this.relation,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt ?? this.createdAt,
      faceCount: faceCount ?? this.faceCount,
    );
  }
}
