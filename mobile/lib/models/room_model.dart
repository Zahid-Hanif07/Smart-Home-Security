class RoomModel {
  const RoomModel({required this.id, required this.name});

  final String id;
  final String name;

  String get normalizedName =>
      name.trim().toLowerCase().replaceAll(RegExp(r'\s+'), ' ');

  factory RoomModel.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final name = json['name'];
    if (id is! String || name is! String || id.isEmpty || name.trim().isEmpty) {
      throw const FormatException('Invalid room response.');
    }
    return RoomModel(id: id, name: name);
  }
}
