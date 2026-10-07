import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/features/members/widgets/member_action_button.dart';

class RegisterFaceScreen extends StatefulWidget {
  const RegisterFaceScreen({super.key});

  @override
  State<RegisterFaceScreen> createState() => _RegisterFaceScreenState();
}

class _RegisterFaceScreenState extends State<RegisterFaceScreen> {
  CameraController? _controller;
  Future<void>? _initializeControllerFuture;
  bool _isCameraInitializing = true;
  String? _cameraError;
  int _currentSamples = 0;
  final int _targetSamples = 8;
  bool _isSuccess = false;
  bool _isCapturing = false;
  String _statusText = 'Position your face inside the frame';

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    setState(() {
      _isCameraInitializing = true;
      _cameraError = null;
    });

    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() {
          _cameraError = 'No camera found on device. Camera is required to register face samples.';
          _isCameraInitializing = false;
        });
        return;
      }

      // Select front camera if available, else first camera
      final camera = cameras.firstWhere(
        (cam) => cam.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      final controller = CameraController(
        camera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );

      _initializeControllerFuture = controller.initialize();
      await _initializeControllerFuture;

      if (mounted) {
        setState(() {
          _controller = controller;
          _isCameraInitializing = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _cameraError = 'Camera error: ${e.toString()}\nPlease check camera permissions.';
          _isCameraInitializing = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _captureSample(BuildContext context, String memberId) async {
    if (_controller == null || !_controller!.value.isInitialized || _isCapturing) {
      return;
    }

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final membersProvider = Provider.of<MembersProvider>(context, listen: false);

    setState(() {
      _isCapturing = true;
      _statusText = 'Processing sample...';
    });

    try {
      final image = await _controller!.takePicture();
      final bytes = await image.readAsBytes();
      final base64Image = base64Encode(bytes);

      final success = await membersProvider.registerFace(
        authProvider.token,
        memberId,
        base64Image,
      );

      if (!mounted) return;

      if (success) {
        final newCount = _currentSamples + 1;
        setState(() {
          _currentSamples = newCount;
          _isCapturing = false;
          if (newCount >= _targetSamples) {
            _isSuccess = true;
            _statusText = 'Face registered successfully!';
          } else {
            _statusText = 'Sample $newCount of $_targetSamples captured. Keep looking at camera.';
          }
        });
      } else {
        setState(() {
          _isCapturing = false;
          _statusText = membersProvider.errorMessage ?? 'Sample capture failed. Please try again.';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCapturing = false;
          _statusText = 'Failed to capture image: ${e.toString()}';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final membersProvider = Provider.of<MembersProvider>(context);
    final member = membersProvider.selectedMember;

    if (member == null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          backgroundColor: AppColors.surface,
          elevation: 0,
          title: const Text('Register Face'),
        ),
        body: const Center(
          child: Text(
            'No member selected for face registration.',
            style: TextStyle(color: AppColors.textPrimary),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: const IconThemeData(color: AppColors.black),
        title: Text(
          'Register Face - ${member.name}',
          style: const TextStyle(
            color: AppColors.textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: AppSpacing.xs),
              Text(
                _isSuccess ? '✓ Face Registered Successfully' : 'Look directly at the camera',
                style: TextStyle(
                  color: _isSuccess ? AppColors.emeraldInk : AppColors.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _isSuccess
                    ? '8 face samples saved to Supabase for ${member.name}.'
                    : 'Position face inside the frame and tap capture to enroll ${member.name}.',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              // Camera Frame / Preview Container
              Container(
                width: double.infinity,
                height: 320,
                decoration: BoxDecoration(
                  color: AppColors.black,
                  borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                  border: Border.all(
                    color: _isSuccess
                        ? AppColors.emeraldInk
                        : (_cameraError != null ? AppColors.error : AppColors.emeraldInk),
                    width: 2,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // Camera preview or fallback
                    if (_isCameraInitializing) ...[
                      const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            CircularProgressIndicator(color: AppColors.champagne),
                            SizedBox(height: 12),
                            Text(
                              'Initializing phone camera...',
                              style: TextStyle(color: AppColors.white, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                    ] else if (_cameraError != null) ...[
                      Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.videocam_off_rounded, color: AppColors.error, size: 48),
                            const SizedBox(height: 12),
                            Text(
                              _cameraError!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: AppColors.white, fontSize: 13),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: _initCamera,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.champagne,
                                foregroundColor: AppColors.black,
                              ),
                              child: const Text('Retry Camera'),
                            ),
                          ],
                        ),
                      ),
                    ] else if (_controller != null && _controller!.value.isInitialized) ...[
                      Positioned.fill(
                        child: CameraPreview(_controller!),
                      ),
                    ],

                    // Success Overlay
                    if (_isSuccess) ...[
                      Container(
                        color: AppColors.black.withValues(alpha: 0.7),
                        width: double.infinity,
                        height: double.infinity,
                        child: const Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.check_circle_rounded, color: AppColors.champagne, size: 64),
                            SizedBox(height: 12),
                            Text(
                              'Enrollment Complete',
                              style: TextStyle(
                                color: AppColors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            SizedBox(height: 4),
                            Text(
                              '128D SFace feature embeddings saved',
                              style: TextStyle(color: AppColors.champagne, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                    ],

                    // Frame Overlay Target Lines (when camera active and not success)
                    if (!_isSuccess && _cameraError == null && !_isCameraInitializing) ...[
                      // Center Guide Frame Oval
                      Container(
                        width: 180,
                        height: 240,
                        decoration: BoxDecoration(
                          shape: BoxShape.rectangle,
                          borderRadius: BorderRadius.circular(90),
                          border: Border.all(
                            color: AppColors.champagne.withValues(alpha: 0.8),
                            width: 2,
                          ),
                        ),
                      ),

                      // Status Overlay Pill at Top
                      Positioned(
                        top: 14,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppColors.black.withValues(alpha: 0.75),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: AppColors.champagne.withValues(alpha: 0.4)),
                          ),
                          child: Text(
                            _statusText,
                            style: const TextStyle(
                              color: AppColors.champagne,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),

                      // Progress Indicator Pill at Bottom
                      Positioned(
                        bottom: 14,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppColors.black.withValues(alpha: 0.75),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Text(
                            'Samples: $_currentSamples / $_targetSamples',
                            style: const TextStyle(
                              color: AppColors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              // Error Message Banner if any
              if (membersProvider.errorMessage != null && !_isSuccess) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpacing.md),
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceSoft,
                    borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                    border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline_rounded, color: AppColors.error, size: 20),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          membersProvider.errorMessage!,
                          style: const TextStyle(
                            color: AppColors.error,
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Controls & Action Buttons
              if (!_isSuccess) ...[
                MemberActionButton(
                  label: _isCapturing
                      ? 'Processing Face Sample...'
                      : (_currentSamples == 0
                          ? 'Capture Sample (1/$_targetSamples)'
                          : 'Capture Sample (${_currentSamples + 1}/$_targetSamples)'),
                  icon: Icons.camera_alt_rounded,
                  isLoading: _isCapturing || membersProvider.isSaving,
                  onPressed: (_cameraError == null && !_isCameraInitializing && !_isCapturing)
                      ? () => _captureSample(context, member.id)
                      : null,
                ),
                const SizedBox(height: AppSpacing.sm),
                MemberActionButton(
                  label: 'Cancel',
                  icon: Icons.close_rounded,
                  isPrimary: false,
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ] else ...[
                MemberActionButton(
                  label: 'Done',
                  icon: Icons.check_circle_outline_rounded,
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
