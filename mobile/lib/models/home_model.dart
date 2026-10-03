class HomeModel {
  final String id;
  final String name;
  final String? address;
  final String? ownerId;
  final DateTime? createdAt;

  HomeModel({
    required this.id,
    required this.name,
    this.address,
    this.ownerId,
    this.createdAt,
  });

  factory HomeModel.fromJson(Map<String, dynamic> json) {
    return HomeModel(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'My Smart Home',
      address: json['address']?.toString(),
      ownerId: json['owner_id']?.toString(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'address': address,
      'owner_id': ownerId,
      'created_at': createdAt?.toIso8601String(),
    };
  }
}
