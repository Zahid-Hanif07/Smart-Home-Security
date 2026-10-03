import 'package:flutter/material.dart';
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
  int _currentSamples = 0;
  final int _targetSamples = 8;
  bool _isSuccess = false;

  /// Generate a valid 1x1 test face pixel or camera capture base64 payload
  String _sampleFaceBase64() {
    return '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';
  }

  void _captureSample(BuildContext context, String memberId) async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final membersProvider = Provider.of<MembersProvider>(context, listen: false);

    setState(() {
      _currentSamples++;
    });

    final success = await membersProvider.registerFace(
      authProvider.token,
      memberId,
      _sampleFaceBase64(),
    );

    if (success && mounted) {
      if (_currentSamples >= _targetSamples) {
        setState(() {
          _isSuccess = true;
        });
      }
    } else if (mounted) {
      setState(() {
        if (_currentSamples > 0) _currentSamples--;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final membersProvider = Provider.of<MembersProvider>(context);
    final member = membersProvider.selectedMember;

    if (member == null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(backgroundColor: AppColors.surface, elevation: 0),
        body: const Center(child: Text('No member selected for face registration.')),
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
              const SizedBox(height: AppSpacing.sm),
              Text(
                _isSuccess ? 'Face Registered Successfully' : 'Look directly at the camera',
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _isSuccess
                    ? '128D SFace feature embeddings saved to Supabase.'
                    : 'Position face in frame and tap capture to enroll ${member.name}.',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              // Camera Frame Preview Box
              Container(
                width: double.infinity,
                height: 280,
                decoration: BoxDecoration(
                  color: AppColors.black,
                  borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                  border: Border.all(
                    color: _isSuccess ? AppColors.success : AppColors.emeraldInk,
                    width: 2,
                  ),
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: _isSuccess
                                ? AppColors.success.withValues(alpha: 0.2)
                                : AppColors.surface.withValues(alpha: 0.15),
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: _isSuccess ? AppColors.success : AppColors.champagne,
                              width: 2,
                            ),
                          ),
                          child: Icon(
                            _isSuccess ? Icons.check_circle_rounded : Icons.face_rounded,
                            color: _isSuccess ? AppColors.success : AppColors.champagne,
                            size: 64,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Text(
                          _isSuccess ? 'Registration Complete' : 'Face Detected',
                          style: TextStyle(
                            color: _isSuccess ? AppColors.success : AppColors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _isSuccess
                              ? '${member.name}\'s face profile active'
                              : 'Samples: $_currentSamples / $_targetSamples',
                          style: const TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),

                    // Target framing overlays
                    Positioned(
                      top: 16,
                      left: 16,
                      child: Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          border: Border(
                            top: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                            left: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      top: 16,
                      right: 16,
                      child: Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          border: Border(
                            top: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                            right: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      bottom: 16,
                      left: 16,
                      child: Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                            left: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      bottom: 16,
                      right: 16,
                      child: Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                            right: BorderSide(
                                color: _isSuccess ? AppColors.success : AppColors.champagne,
                                width: 3),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              if (membersProvider.errorMessage != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpacing.md),
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceSoft,
                    borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                    border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    membersProvider.errorMessage!,
                    style: const TextStyle(
                      color: AppColors.error,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],

              if (!_isSuccess) ...[
                MemberActionButton(
                  label: _currentSamples == 0 ? 'Capture Face Sample' : 'Capture Sample (${_currentSamples + 1}/$_targetSamples)',
                  icon: Icons.camera_alt_rounded,
                  isLoading: membersProvider.isSaving,
                  onPressed: () => _captureSample(context, member.id),
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
