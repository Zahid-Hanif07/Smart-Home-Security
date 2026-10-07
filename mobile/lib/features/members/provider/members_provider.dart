import 'package:flutter/foundation.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/models/member_model.dart';
import 'package:mobile/models/face_record_model.dart';

class MembersProvider extends ChangeNotifier {
  final ApiClient _apiClient;

  List<MemberModel> _members = [];
  MemberModel? _selectedMember;
  List<FaceRecordModel> _memberFaces = [];
  bool _isLoading = false;
  bool _isSaving = false;
  String? _errorMessage;
  String? _successMessage;

  MembersProvider({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  List<MemberModel> get members => _members;
  MemberModel? get selectedMember => _selectedMember;
  List<FaceRecordModel> get memberFaces => _memberFaces;
  bool get isLoading => _isLoading;
  bool get isSaving => _isSaving;
  String? get errorMessage => _errorMessage;
  String? get successMessage => _successMessage;

  void clearMessages() {
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();
  }

  void selectMember(MemberModel? member) {
    _selectedMember = member;
    _memberFaces = [];
    notifyListeners();
  }

  Future<void> loadMembers(String? token, String homeId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final rawList = await _apiClient.getMembers(homeId, token);
      _members = rawList.map((json) => MemberModel.fromJson(json as Map<String, dynamic>)).toList();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Failed to load family members: ${e.toString()}';
      notifyListeners();
    }
  }

  Future<MemberModel?> addMember(String? token, String homeId, String name, String? relation) async {
    if (name.trim().isEmpty) {
      _errorMessage = 'Member name cannot be empty.';
      notifyListeners();
      return null;
    }

    _isSaving = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final body = {
        'name': name.trim(),
        'relation': relation?.trim(),
      };
      final res = await _apiClient.createMember(homeId, body, token);
      final newMember = MemberModel.fromJson(res as Map<String, dynamic>);
      _members.add(newMember);
      _selectedMember = newMember;
      _isSaving = false;
      _successMessage = '${newMember.name} added successfully.';
      notifyListeners();
      return newMember;
    } catch (e) {
      _isSaving = false;
      _errorMessage = 'Failed to add family member: ${e.toString()}';
      notifyListeners();
      return null;
    }
  }

  Future<bool> updateMember(String? token, String memberId, String name, String? relation) async {
    _isSaving = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final body = {
        'name': name.trim(),
        'relation': relation?.trim(),
      };
      final res = await _apiClient.updateMember(memberId, body, token);
      final updated = MemberModel.fromJson(res as Map<String, dynamic>);
      
      final index = _members.indexWhere((m) => m.id == memberId);
      if (index != -1) {
        _members[index] = updated;
      }
      if (_selectedMember?.id == memberId) {
        _selectedMember = updated;
      }
      _isSaving = false;
      _successMessage = 'Member updated successfully.';
      notifyListeners();
      return true;
    } catch (e) {
      _isSaving = false;
      _errorMessage = 'Failed to update member: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteMember(String? token, String memberId) async {
    _isSaving = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _apiClient.deleteMember(memberId, token);
      _members.removeWhere((m) => m.id == memberId);
      if (_selectedMember?.id == memberId) {
        _selectedMember = null;
        _memberFaces = [];
      }
      _isSaving = false;
      _successMessage = 'Member removed successfully.';
      notifyListeners();
      return true;
    } catch (e) {
      _isSaving = false;
      _errorMessage = 'Failed to delete member: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<void> loadMemberFaces(String? token, String memberId) async {
    try {
      final rawList = await _apiClient.getFaces(memberId, token);
      _memberFaces = rawList.map((json) => FaceRecordModel.fromJson(json as Map<String, dynamic>)).toList();
      
      // Update faceCount on selected member if needed
      if (_selectedMember?.id == memberId) {
        _selectedMember = _selectedMember!.copyWith(faceCount: _memberFaces.length);
        final idx = _members.indexWhere((m) => m.id == memberId);
        if (idx != -1) {
          _members[idx] = _selectedMember!;
        }
      }
      notifyListeners();
    } catch (e) {
      _errorMessage = 'Failed to load face records: ${e.toString()}';
      notifyListeners();
    }
  }

  Future<bool> registerFace(String? token, String memberId, String imageBase64) async {
    _isSaving = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final body = {
        'image_base64': imageBase64,
        'sample_count': 1,
      };
      final res = await _apiClient.registerFace(memberId, body, token);
      final newFace = FaceRecordModel.fromJson(res as Map<String, dynamic>);
      _memberFaces.add(newFace);

      if (_selectedMember?.id == memberId) {
        _selectedMember = _selectedMember!.copyWith(faceCount: _memberFaces.length);
        final idx = _members.indexWhere((m) => m.id == memberId);
        if (idx != -1) {
          _members[idx] = _selectedMember!;
        }
      }

      _isSaving = false;
      _successMessage = 'Face registered successfully!';
      notifyListeners();
      return true;
    } catch (e) {
      _isSaving = false;
      _errorMessage = 'Face registration failed: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteFace(String? token, String faceId) async {
    _isSaving = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _apiClient.deleteFace(faceId, token);
      _memberFaces.removeWhere((f) => f.id == faceId);

      if (_selectedMember != null) {
        _selectedMember = _selectedMember!.copyWith(faceCount: _memberFaces.length);
        final idx = _members.indexWhere((m) => m.id == _selectedMember!.id);
        if (idx != -1) {
          _members[idx] = _selectedMember!;
        }
      }

      _isSaving = false;
      _successMessage = 'Face record removed.';
      notifyListeners();
      return true;
    } catch (e) {
      _isSaving = false;
      _errorMessage = 'Failed to delete face record: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }

  Future<bool> clearMemberFaces(String? token, String memberId) async {
    _isSaving = true;
    _errorMessage = null;
    notifyListeners();

    try {
      await _apiClient.clearMemberFaces(memberId, token);
      _memberFaces = [];

      if (_selectedMember?.id == memberId) {
        _selectedMember = _selectedMember!.copyWith(faceCount: 0);
        final idx = _members.indexWhere((m) => m.id == memberId);
        if (idx != -1) {
          _members[idx] = _selectedMember!;
        }
      }

      _isSaving = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isSaving = false;
      _errorMessage = 'Failed to clear previous face records: ${e.toString()}';
      notifyListeners();
      return false;
    }
  }
}
