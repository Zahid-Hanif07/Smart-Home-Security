import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/features/members/widgets/member_action_button.dart';

class RegisterFaceScreen extends StatelessWidget {
  const RegisterFaceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final membersProvider = Provider.of<MembersProvider>(context);
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final member = membersProvider.selectedMember;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (member != null) membersProvider.initializeCamera();
    });

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
                membersProvider.faceRegistrationSuccess ? '✓ Face Registered Successfully' : 'Look directly at the camera',
                style: TextStyle(
                  color: membersProvider.faceRegistrationSuccess ? AppColors.emeraldInk : AppColors.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                membersProvider.faceRegistrationSuccess
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
                    color: membersProvider.faceRegistrationSuccess
                        ? AppColors.emeraldInk
                        : (membersProvider.cameraError != null ? AppColors.error : AppColors.emeraldInk),
                    width: 2,
                  ),
                ),
                clipBehavior: Clip.antiAlias,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // Camera preview or fallback
                    if (membersProvider.isCameraInitializing) ...[
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
                    ] else if (membersProvider.cameraError != null) ...[
                      Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.videocam_off_rounded, color: AppColors.error, size: 48),
                            const SizedBox(height: 12),
                            Text(
                              membersProvider.cameraError!,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: AppColors.white, fontSize: 13),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: membersProvider.retryCameraInitialization,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.champagne,
                                foregroundColor: AppColors.black,
                              ),
                              child: const Text('Retry Camera'),
                            ),
                          ],
                        ),
                      ),
                    ] else if (membersProvider.cameraController != null && membersProvider.cameraController!.value.isInitialized) ...[
                      Positioned.fill(
                        child: CameraPreview(membersProvider.cameraController!),
                      ),
                    ],

                    // Success Overlay
                    if (membersProvider.faceRegistrationSuccess) ...[
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
                    if (!membersProvider.faceRegistrationSuccess && membersProvider.cameraError == null && !membersProvider.isCameraInitializing) ...[
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
                            membersProvider.faceStatusText,
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
                            'Samples: ${membersProvider.currentFaceSamples} / ${membersProvider.targetFaceSamples}',
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
              if (membersProvider.errorMessage != null && !membersProvider.faceRegistrationSuccess) ...[
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
              if (!membersProvider.faceRegistrationSuccess) ...[
                MemberActionButton(
                  label: membersProvider.isCapturingFace
                      ? 'Processing Face Sample...'
                      : (membersProvider.currentFaceSamples == 0
                          ? 'Capture Sample (1/${membersProvider.targetFaceSamples})'
                          : 'Capture Sample (${membersProvider.currentFaceSamples + 1}/${membersProvider.targetFaceSamples})'),
                  icon: Icons.camera_alt_rounded,
                  isLoading: membersProvider.isCapturingFace || membersProvider.isSaving,
                  onPressed: (membersProvider.cameraError == null && !membersProvider.isCameraInitializing && !membersProvider.isCapturingFace)
                      ? () => membersProvider.captureFaceSample(authProvider.token, member.id)
                      : null,
                ),
                const SizedBox(height: AppSpacing.sm),
                MemberActionButton(
                  label: 'Cancel',
                  icon: Icons.close_rounded,
                  isPrimary: false,
                  onPressed: () async {
                    await membersProvider.closeFaceRegistration();
                    if (context.mounted) Navigator.of(context).pop();
                  },
                ),
              ] else ...[
                MemberActionButton(
                  label: 'Done',
                  icon: Icons.check_circle_outline_rounded,
                  onPressed: () async {
                    await membersProvider.closeFaceRegistration();
                    if (context.mounted) Navigator.of(context).pop();
                  },
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
