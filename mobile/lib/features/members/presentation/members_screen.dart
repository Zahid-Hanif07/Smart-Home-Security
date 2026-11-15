import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/core/widgets/floating_capsule_navigation.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/features/members/widgets/member_list_item.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

class MembersScreen extends StatelessWidget {
  const MembersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final homeProvider = context.watch<HomeProvider>();
    final members = context.watch<MembersProvider>();
    final home = homeProvider.currentHome;
    final homeId = home?.id ?? '';
    final faceReadyCount = members.members.where((member) => member.faceCount > 0).length;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      members.ensureMembersLoaded(auth.token, homeId);
    });

    void openAddMember() {
      if (homeId.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please select or create a home first.'), backgroundColor: AppColors.error));
        return;
      }
      Navigator.of(context).pushNamed(AppRoutes.addMember);
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        scrolledUnderElevation: 0,
        title: const Text('OTTO', style: TextStyle(color: AppColors.emeraldInk, fontSize: 15, letterSpacing: 3, fontWeight: FontWeight.w800)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 18),
            child: InkWell(
              borderRadius: BorderRadius.circular(30),
              onTap: () => Navigator.of(context).pushNamed(AppRoutes.profile),
              child: CircleAvatar(
                radius: 18,
                backgroundColor: AppColors.champagne,
                foregroundColor: AppColors.emeraldInk,
                child: Text((auth.currentUser?.name.isNotEmpty ?? false) ? auth.currentUser!.name[0].toUpperCase() : 'H', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
              ),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.emeraldInk,
        backgroundColor: AppColors.surface,
        onRefresh: () async {
          if (homeId.isNotEmpty) await members.loadMembers(auth.token, homeId, forceRefresh: true);
        },
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(22, 7, 22, 24),
          children: [
            Text((home?.name ?? 'YOUR HOME').toUpperCase(), style: const TextStyle(fontSize: 9, letterSpacing: 1.15, fontWeight: FontWeight.w700, color: AppColors.textSecondary)),
            const SizedBox(height: 5),
            Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
              const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('People', style: TextStyle(fontSize: 27, height: 1.1, fontWeight: FontWeight.w700, letterSpacing: -.8, color: AppColors.textPrimary)),
                SizedBox(height: 4),
                Text('Trusted faces with access to your home.', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              ])),
              Material(color: AppColors.emeraldInk, borderRadius: BorderRadius.circular(12), child: InkWell(onTap: openAddMember, borderRadius: BorderRadius.circular(12), child: const SizedBox(width: 38, height: 38, child: Icon(Icons.person_add_alt_1_rounded, color: AppColors.white, size: 17)))),
            ]),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: AppColors.emeraldInk, borderRadius: BorderRadius.circular(15)),
              child: Row(children: [
                Container(width: 34, height: 34, decoration: BoxDecoration(color: AppColors.white.withValues(alpha: .12), borderRadius: BorderRadius.circular(10)), child: const Icon(Icons.face_retouching_natural_rounded, color: AppColors.lime, size: 18)),
                const SizedBox(width: 10),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(homeId.isEmpty ? 'Select a home to manage access' : (faceReadyCount > 0 ? 'Face recognition ready' : 'Face enrollment available'), style: const TextStyle(color: AppColors.white, fontSize: 11, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text('$faceReadyCount trusted ${faceReadyCount == 1 ? 'person' : 'people'} enrolled', style: const TextStyle(color: Color(0xFFD0DED5), fontSize: 9)),
                ])),
              ]),
            ),
            const SizedBox(height: 17),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              const Text('Home members', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
              Text('${members.members.length} ${members.members.length == 1 ? 'person' : 'people'}', style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600, color: AppColors.forest)),
            ]),
            if (members.errorMessage != null) ...[
              const SizedBox(height: 8),
              Text(members.errorMessage!, style: const TextStyle(color: AppColors.error, fontSize: 11)),
            ],
            if (members.isLoading && members.members.isEmpty)
              const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator(color: AppColors.emeraldInk)))
            else if (homeId.isEmpty)
              Padding(padding: const EdgeInsets.symmetric(vertical: 16), child: TextButton.icon(onPressed: () => Navigator.of(context).pushNamed(AppRoutes.homes), icon: const Icon(Icons.home_work_outlined), label: const Text('Select or add a home')))
            else ...[
              ...members.members.map((member) => MemberListItem(
                member: member,
                homeName: home?.name,
                onTap: () {
                  members.selectMember(member);
                  Navigator.of(context).pushNamed(AppRoutes.memberDetail);
                },
              )),
              InkWell(
                onTap: openAddMember,
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.border))),
                  child: Row(children: [
                    Container(width: 42, height: 42, decoration: const BoxDecoration(color: AppColors.mint, shape: BoxShape.circle), child: const Icon(Icons.add_rounded, color: AppColors.forest, size: 20)),
                    const SizedBox(width: 11),
                    const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Invite someone you trust', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.textPrimary)), SizedBox(height: 3), Text('Add a family member or housemate', style: TextStyle(fontSize: 9, color: AppColors.textSecondary))])),
                    const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted, size: 18),
                  ]),
                ),
              ),
            ],
            const SizedBox(height: 12),
            SizedBox(
              height: 40,
              child: ElevatedButton.icon(
                onPressed: openAddMember,
                icon: const Icon(Icons.person_add_alt_1_rounded, size: 14),
                label: const Text('Add a member', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                style: ElevatedButton.styleFrom(backgroundColor: AppColors.emeraldInk, foregroundColor: AppColors.white, minimumSize: const Size.fromHeight(40), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
              ),
            ),
            const SizedBox(height: 14),
            const Text('Access note', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
            const SizedBox(height: 4),
            const Text('Only people enrolled for this home are used for trusted face recognition.', style: TextStyle(fontSize: 10, height: 1.45, color: AppColors.textSecondary)),
            const SizedBox(height: AppSpacing.sm),
          ],
        ),
      ),
      bottomNavigationBar: const FloatingCapsuleNavigation(selectedIndex: 1),
    );
  }
}
