import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/features/members/widgets/member_avatar.dart';
import 'package:mobile/features/members/widgets/member_action_button.dart';

class MemberDetailScreen extends StatelessWidget {
  const MemberDetailScreen({super.key});

  void _initFaces(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final membersProvider = Provider.of<MembersProvider>(context, listen: false);
      final member = membersProvider.selectedMember;

      if (member != null) {
        membersProvider.ensureMemberFacesLoaded(authProvider.token, member.id);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    _initFaces(context);

    final authProvider = Provider.of<AuthProvider>(context);
    final membersProvider = Provider.of<MembersProvider>(context);
    final member = membersProvider.selectedMember;

    if (member == null) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          backgroundColor: AppColors.surface,
          elevation: 0,
          title: const Text('Member Detail'),
        ),
        body: const Center(
          child: Text(
            'No member selected.',
            style: TextStyle(color: AppColors.textPrimary),
          ),
        ),
      );
    }

    final hasRegisteredFace = membersProvider.memberFaces.isNotEmpty || member.faceCount > 0;
    final sampleCount = membersProvider.memberFaces.isNotEmpty
        ? membersProvider.memberFaces.length
        : member.faceCount;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: const IconThemeData(color: AppColors.black),
        title: Text(
          member.name,
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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Avatar & Name Card
              Center(
                child: Column(
                  children: [
                    MemberAvatar(
                      name: member.name,
                      size: 72,
                      hasRegisteredFace: hasRegisteredFace,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      member.name,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (member.relation != null && member.relation!.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        member.relation!,
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xl),

              // Feedback messages
              if (membersProvider.successMessage != null) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpacing.md),
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.champagne,
                    borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                    border: Border.all(color: AppColors.emeraldInk.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    membersProvider.successMessage!,
                    style: const TextStyle(
                      color: AppColors.black,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],

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

              // ---------------------------------------------------------------
              // SECTION: MEMBER
              // ---------------------------------------------------------------
              const Text(
                'MEMBER',
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.0,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Name:',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      member.name,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Relationship:',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      (member.relation != null && member.relation!.isNotEmpty)
                          ? member.relation!
                          : 'Not Specified',
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              // ---------------------------------------------------------------
              // SECTION: FACE
              // ---------------------------------------------------------------
              const Text(
                'FACE',
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.0,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Face Status',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Text(
                          hasRegisteredFace ? '✓ Face Registered' : '● Not Registered',
                          style: TextStyle(
                            color: hasRegisteredFace ? AppColors.emeraldInk : AppColors.error,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                    if (hasRegisteredFace) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Registered Samples: $sampleCount',
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                    const SizedBox(height: AppSpacing.md),

                    MemberActionButton(
                      label: hasRegisteredFace ? 'Re-register Face' : 'Register Face',
                      icon: Icons.camera_alt_rounded,
                      onPressed: () async {
                        if (hasRegisteredFace) {
                          // Clear previous face records safely when re-registering
                          final confirm = await showDialog<bool>(
                            context: context,
                            builder: (ctx) => AlertDialog(
                              backgroundColor: AppColors.surface,
                              title: const Text('Re-register Face'),
                              content: Text(
                                  'This will replace existing face samples for ${member.name}. Proceed?'),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.of(ctx).pop(false),
                                  child: const Text('Cancel',
                                      style: TextStyle(color: AppColors.textSecondary)),
                                ),
                                TextButton(
                                  onPressed: () => Navigator.of(ctx).pop(true),
                                  child: const Text('Proceed',
                                      style: TextStyle(
                                          color: AppColors.emeraldInk,
                                          fontWeight: FontWeight.w700)),
                                ),
                              ],
                            ),
                          );

                          if (confirm == true && context.mounted) {
                            await membersProvider.clearMemberFaces(authProvider.token, member.id);
                            if (context.mounted) {
                              Navigator.of(context).pushNamed(AppRoutes.registerFace);
                            }
                          }
                        } else {
                          Navigator.of(context).pushNamed(AppRoutes.registerFace);
                        }
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.xl),

              // Delete Member Button
              MemberActionButton(
                label: 'Delete Family Member',
                icon: Icons.delete_outline_rounded,
                isPrimary: false,
                isLoading: membersProvider.isSaving,
                onPressed: () async {
                  final confirm = await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      backgroundColor: AppColors.surface,
                      title: const Text('Delete Member'),
                      content: Text(
                          'Are you sure you want to remove ${member.name} and all associated face records?'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.of(ctx).pop(false),
                          child: const Text('Cancel',
                              style: TextStyle(color: AppColors.textSecondary)),
                        ),
                        TextButton(
                          onPressed: () => Navigator.of(ctx).pop(true),
                          child: const Text('Delete',
                              style: TextStyle(
                                  color: AppColors.error, fontWeight: FontWeight.w700)),
                        ),
                      ],
                    ),
                  );

                  if (confirm == true && context.mounted) {
                    final success =
                        await membersProvider.deleteMember(authProvider.token, member.id);
                    if (success && context.mounted) {
                      Navigator.of(context).pop();
                    }
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
