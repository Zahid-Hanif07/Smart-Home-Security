class AlertModel {
  final String id;
  final String homeId;
  final String type;
  final String title;
  final String message;
  final String? imagePath;
  final bool isRead;
  final DateTime createdAt;

  const AlertModel({
    required this.id,
    required this.homeId,
    required this.type,
    required this.title,
    required this.message,
    required this.isRead,
    required this.createdAt,
    this.imagePath,
  });

  factory AlertModel.fromJson(Map<String, dynamic> json) => AlertModel(
    id: json['id']?.toString() ?? '',
    homeId: json['home_id']?.toString() ?? '',
    type: json['alert_type']?.toString() ?? 'security_event',
    title: json['title']?.toString() ?? 'Security alert',
    message: json['message']?.toString() ?? '',
    imagePath: json['image_path']?.toString(),
    isRead: json['is_read'] == true,
    createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
  );
}
