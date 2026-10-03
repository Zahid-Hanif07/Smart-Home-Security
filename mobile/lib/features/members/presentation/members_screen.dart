import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/features/members/widgets/member_list_item.dart';
import 'package:mobile/features/members/widgets/member_empty_state.dart';

class MembersScreen extends StatelessWidget {
  const MembersScreen({super.key});

  void _initMembers(BuildContext context) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final homeProvider = Provider.of<HomeProvider>(context, listen: false);
      final membersProvider = Provider.of<MembersProvider>(context, listen: false);

      final homeId = homeProvider.currentHome?.id;
      if (homeId != null && homeId.isNotEmpty) {
        membersProvider.loadMembers(authProvider.token, homeId);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    _initMembers(context);

    final authProvider = Provider.of<AuthProvider>(context);
    final homeProvider = Provider.of<HomeProvider>(context);
    final membersProvider = Provider.of<MembersProvider>(context);

    final homeId = homeProvider.currentHome?.id ?? '';

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: const IconThemeData(color: AppColors.black),
        title: const Text(
          'Family Members',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.black,
          backgroundColor: AppColors.surface,
          onRefresh: () async {
            if (homeId.isNotEmpty) {
              await membersProvider.loadMembers(authProvider.token, homeId);
            }
          },
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Header Banner & Add Button
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          homeProvider.currentHome?.name ?? 'Main Residence',
                          style: const TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${membersProvider.members.length} Members Enrolled',
                          style: const TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                    ElevatedButton.icon(
                      onPressed: () {
                        Navigator.of(context).pushNamed(AppRoutes.addMember);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.emeraldInk,
                        foregroundColor: AppColors.white,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(AppSpacing.buttonRadius),
                        ),
                      ),
                      icon: const Icon(Icons.add_rounded, size: 18),
                      label: const Text(
                        'Add Member',
                        style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.lg),

                // Error Message if any
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

                // Loading Indicator or List
                if (membersProvider.isLoading) ...[
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 40),
                    child: Center(
                      child: CircularProgressIndicator(color: AppColors.black),
                    ),
                  ),
                ] else if (membersProvider.members.isEmpty) ...[
                  MemberEmptyState(
                    onAddMember: () {
                      Navigator.of(context).pushNamed(AppRoutes.addMember);
                    },
                  ),
                ] else ...[
                  ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: membersProvider.members.length,
                    itemBuilder: (context, index) {
                      final member = membersProvider.members[index];
                      return MemberListItem(
                        member: member,
                        onTap: () {
                          membersProvider.selectMember(member);
                          Navigator.of(context).pushNamed(AppRoutes.memberDetail);
                        },
                      );
                    },
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
