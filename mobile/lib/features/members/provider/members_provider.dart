import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
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
  final addMemberNameController = TextEditingController();
  final addMemberRelationController = TextEditingController();
  String? _lastLoadedHomeId;
  bool _hasLoadedMembers = false;
  CameraController? cameraController;
  Future<void>? cameraInitialization;
  bool isCameraInitializing = true;
  String? cameraError;
  int currentFaceSamples = 0;
  final int targetFaceSamples = 8;
  bool faceRegistrationSuccess = false;
  bool isCapturingFace = false;
  String faceStatusText = 'Position your face inside the frame';
  bool _cameraInitializationStarted = false;
  int _cameraRequestId = 0;
  String? _facesLoadedForMemberId;
  String? _facesLoadingForMemberId;

  Future<void> initializeCamera() async {
    if (_cameraInitializationStarted) return;
    _cameraInitializationStarted = true;
    final requestId = ++_cameraRequestId;
    isCameraInitializing = true;
    cameraError = null;
    notifyListeners();
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        cameraError = 'No camera found on device. Camera is required to register face samples.';
        isCameraInitializing = false;
        notifyListeners();
        return;
      }
      final camera = cameras.firstWhere(
        (item) => item.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        camera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      cameraInitialization = controller.initialize();
      await cameraInitialization;
      if (requestId != _cameraRequestId) {
        await controller.dispose();
        return;
      }
      cameraController = controller;
      isCameraInitializing = false;
      notifyListeners();
    } catch (error) {
      if (requestId != _cameraRequestId) return;
      cameraError = 'Camera error: $error\nPlease check camera permissions.';
      isCameraInitializing = false;
      notifyListeners();
    }
  }

  Future<void> retryCameraInitialization() async {
    _cameraRequestId++;
    await cameraController?.dispose();
    cameraController = null;
    cameraInitialization = null;
    _cameraInitializationStarted = false;
    await initializeCamera();
  }

  Future<void> closeFaceRegistration() async {
    _cameraRequestId++;
    await cameraController?.dispose();
    cameraController = null;
    cameraInitialization = null;
    _cameraInitializationStarted = false;
    isCameraInitializing = true;
    cameraError = null;
    currentFaceSamples = 0;
    faceRegistrationSuccess = false;
    isCapturingFace = false;
    faceStatusText = 'Position your face inside the frame';
    notifyListeners();
  }

  Future<void> captureFaceSample(String? token, String memberId) async {
    final controller = cameraController;
    if (controller == null || !controller.value.isInitialized || isCapturingFace) return;
    isCapturingFace = true;
    faceStatusText = 'Processing sample...';
    notifyListeners();
    try {
      final image = await controller.takePicture();
      final bytes = await image.readAsBytes();
      final success = await registerFace(token, memberId, base64Encode(bytes));
      if (success) {
        currentFaceSamples++;
        if (currentFaceSamples >= targetFaceSamples) {
          faceRegistrationSuccess = true;
          faceStatusText = 'Face registered successfully!';
        } else {
          faceStatusText = 'Sample $currentFaceSamples of $targetFaceSamples captured. Keep looking at camera.';
        }
      } else {
        faceStatusText = errorMessage ?? 'Sample capture failed. Please try again.';
      }
    } catch (error) {
      faceStatusText = 'Failed to capture image: $error';
    } finally {
      isCapturingFace = false;
      notifyListeners();
    }
  }

  Future<void> ensureMembersLoaded(String? token, String? homeId) async {
    final id = homeId ?? '';
    if (id == _lastLoadedHomeId && (isLoading || _hasLoadedMembers)) return;
    if (id != _lastLoadedHomeId) _hasLoadedMembers = false;
    _lastLoadedHomeId = id;
    if (id.isEmpty) _hasLoadedMembers = true;
    await loadMembers(token, id);
  }

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
    _facesLoadedForMemberId = null;
    _facesLoadingForMemberId = null;
    notifyListeners();
  }

  Future<void> ensureMemberFacesLoaded(String? token, String memberId) async {
    if (_facesLoadedForMemberId == memberId || _facesLoadingForMemberId == memberId) return;
    _facesLoadingForMemberId = memberId;
    await loadMemberFaces(token, memberId);
    _facesLoadingForMemberId = null;
    _facesLoadedForMemberId = memberId;
  }

  Future<void> loadMembers(String? token, String homeId, {bool forceRefresh = false}) async {
    final cleanHomeId = homeId.trim();
    if (cleanHomeId.isEmpty) {
      _members = [];
      _isLoading = false;
      _errorMessage = 'Please select or create a home first.';
      notifyListeners();
      return;
    }

    if (_isLoading && !forceRefresh) return;

    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final rawList = await _apiClient.getMembers(cleanHomeId, token);
      _members = rawList.map((json) => MemberModel.fromJson(json as Map<String, dynamic>)).toList();
      _hasLoadedMembers = true;
      _isLoading = false;
      _hasLoadedMembers = true;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      _errorMessage = 'Failed to load family members: ${e.toString()}';
      notifyListeners();
    }
  }

  Future<MemberModel?> addMember(String? token, String homeId, String name, String? relation) async {
    if (homeId.trim().isEmpty) {
      _errorMessage = 'Please select or create a home first.';
      notifyListeners();
      return null;
    }

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
      addMemberNameController.clear();
      addMemberRelationController.clear();
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

  @override
  void dispose() {
    cameraController?.dispose();
    addMemberNameController.dispose();
    addMemberRelationController.dispose();
    super.dispose();
  }
}
