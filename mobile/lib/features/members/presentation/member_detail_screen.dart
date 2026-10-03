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
        membersProvider.loadMemberFaces(authProvider.token, member.id);
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
        appBar: AppBar(backgroundColor: AppColors.surface, elevation: 0),
        body: const Center(
          child: Text('No member selected.'),
        ),
      );
    }

    final hasRegisteredFace = membersProvider.memberFaces.isNotEmpty || member.faceCount > 0;

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
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: AppSpacing.md),
              MemberAvatar(
                name: member.name,
                size: 72,
                hasRegisteredFace: hasRegisteredFace,
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                member.name,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (member.relation != null && member.relation!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  member.relation!,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: hasRegisteredFace ? AppColors.champagne : AppColors.surfaceSoft,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: hasRegisteredFace ? AppColors.emeraldInk.withValues(alpha: 0.5) : AppColors.border,
                  ),
                ),
                child: Text(
                  hasRegisteredFace ? 'Face Registered' : 'Face Not Registered',
                  style: TextStyle(
                    color: hasRegisteredFace ? AppColors.black : AppColors.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
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

              // Face Registration Records Card
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
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Registered Face Embeddings',
                          style: TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Text(
                          '${membersProvider.memberFaces.length} Records',
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.md),

                    if (membersProvider.memberFaces.isEmpty) ...[
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          'No face records enrolled yet. Register a face sample to enable camera recognition for this member.',
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ] else ...[
                      ListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: membersProvider.memberFaces.length,
                        itemBuilder: (context, idx) {
                          final face = membersProvider.memberFaces[idx];
                          return Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: AppColors.surfaceSoft,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.face_rounded,
                                  color: AppColors.black,
                                  size: 20,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '128D SFace Embedding Sample #${idx + 1}',
                                        style: const TextStyle(
                                          color: AppColors.textPrimary,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        'Registered: ${face.createdAt.toString().split('.')[0]}',
                                        style: const TextStyle(
                                          color: AppColors.textMuted,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                IconButton(
                                  icon: const Icon(
                                    Icons.delete_outline_rounded,
                                    color: AppColors.error,
                                    size: 20,
                                  ),
                                  onPressed: () async {
                                    await membersProvider.deleteFace(authProvider.token, face.id);
                                  },
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.lg),

              // Action Buttons
              MemberActionButton(
                label: 'Register Face Sample',
                icon: Icons.camera_alt_rounded,
                onPressed: () {
                  Navigator.of(context).pushNamed(AppRoutes.registerFace);
                },
              ),
              const SizedBox(height: AppSpacing.sm),

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
                      content: Text('Are you sure you want to remove ${member.name} and their face records?'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.of(ctx).pop(false),
                          child: const Text('Cancel', style: TextStyle(color: AppColors.textSecondary)),
                        ),
                        TextButton(
                          onPressed: () => Navigator.of(ctx).pop(true),
                          child: const Text('Delete', style: TextStyle(color: AppColors.error, fontWeight: FontWeight.w700)),
                        ),
                      ],
                    ),
                  );

                  if (confirm == true && context.mounted) {
                    final success = await membersProvider.deleteMember(authProvider.token, member.id);
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
