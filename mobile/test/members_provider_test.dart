import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/models/member_model.dart';
import 'package:mobile/models/face_record_model.dart';

void main() {
  group('MembersProvider Unit Tests', () {
    test('1. MembersProvider initial state is empty', () {
      final provider = MembersProvider();
      expect(provider.members, isEmpty);
      expect(provider.selectedMember, isNull);
      expect(provider.memberFaces, isEmpty);
      expect(provider.isLoading, false);
      expect(provider.isSaving, false);
      expect(provider.errorMessage, isNull);
    });

    test('2. Select member updates selectedMember state', () {
      final provider = MembersProvider();
      final member = MemberModel(
        id: 'mem-1',
        homeId: 'home-1',
        name: 'Zahid',
        relation: 'Owner',
        createdAt: DateTime.now(),
      );

      provider.selectMember(member);
      expect(provider.selectedMember?.id, 'mem-1');
      expect(provider.selectedMember?.name, 'Zahid');
    });

    test('3. MemberModel and FaceRecordModel JSON serialization', () {
      final memberJson = {
        'id': 'mem-101',
        'home_id': 'home-202',
        'name': 'Amish',
        'relation': 'Brother',
        'created_at': '2026-10-01T10:00:00.000Z',
        'face_count': 2,
      };

      final member = MemberModel.fromJson(memberJson);
      expect(member.id, 'mem-101');
      expect(member.name, 'Amish');
      expect(member.relation, 'Brother');
      expect(member.faceCount, 2);

      final faceJson = {
        'id': 'face-1',
        'member_id': 'mem-101',
        'sample_count': 1,
        'created_at': '2026-10-01T10:05:00.000Z',
      };

      final face = FaceRecordModel.fromJson(faceJson);
      expect(face.id, 'face-1');
      expect(face.memberId, 'mem-101');
    });
  });
}
