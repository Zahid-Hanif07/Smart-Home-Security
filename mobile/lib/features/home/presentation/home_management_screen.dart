import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/core/widgets/floating_capsule_navigation.dart';
import 'package:mobile/models/home_model.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

class HomeManagementScreen extends StatelessWidget {
  const HomeManagementScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final homes = context.watch<HomeProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) => homes.initializeHomeManagement(auth.token));

    Future<void> openHome(HomeModel home) async {
      await homes.selectHome(home, auth.token);
      if (context.mounted) Navigator.of(context).pushNamed(AppRoutes.home);
    }

    Future<void> openMembers(HomeModel home) async {
      await homes.selectHome(home, auth.token);
      if (context.mounted) Navigator.of(context).pushNamed(AppRoutes.members);
    }

    Future<void> editHome(HomeModel home) async {
      await homes.selectHome(home, auth.token);
      if (context.mounted) Navigator.of(context).pushNamed(AppRoutes.editHome);
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
              borderRadius: BorderRadius.circular(24),
              onTap: () => Navigator.of(context).pushNamed(AppRoutes.profile),
              child: CircleAvatar(radius: 18, backgroundColor: AppColors.champagne, foregroundColor: AppColors.emeraldInk, child: Text((auth.currentUser?.name.isNotEmpty ?? false) ? auth.currentUser!.name[0].toUpperCase() : 'H', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700))),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.emeraldInk,
        backgroundColor: AppColors.surface,
        onRefresh: () => homes.fetchHomes(auth.token),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(22, 7, 22, 24),
          children: [
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('YOUR SECURITY LOCATIONS', style: TextStyle(fontSize: 9, letterSpacing: 1.15, fontWeight: FontWeight.w700, color: AppColors.textSecondary)),
                SizedBox(height: 5),
                Text('Homes', style: TextStyle(fontSize: 27, height: 1.1, fontWeight: FontWeight.w700, letterSpacing: -.8, color: AppColors.textPrimary)),
                SizedBox(height: 4),
                Text('Manage the places you protect.', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              ])),
              Material(color: AppColors.emeraldInk, borderRadius: BorderRadius.circular(12), child: InkWell(onTap: () => Navigator.of(context).pushNamed(AppRoutes.addHome), borderRadius: BorderRadius.circular(12), child: const SizedBox(width: 38, height: 38, child: Icon(Icons.add_rounded, color: AppColors.white, size: 20)))),
            ]),
            const SizedBox(height: 15),
            if (homes.errorMessage != null)
              Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.champagneSoft, borderRadius: BorderRadius.circular(12)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(homes.errorMessage!, style: const TextStyle(color: AppColors.error, fontSize: 11)), if (homes.homes.isEmpty) TextButton(onPressed: () => homes.retryInitialHomeSetup(auth.token), child: const Text('Retry home setup'))])),
            if (homes.isLoading && homes.homes.isEmpty)
              const Padding(padding: EdgeInsets.symmetric(vertical: 38), child: Center(child: CircularProgressIndicator(color: AppColors.emeraldInk)))
            else if (homes.homes.isEmpty)
              Padding(padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 12), child: Column(children: [
                const Icon(Icons.home_work_outlined, size: 38, color: AppColors.textMuted),
                const SizedBox(height: 12),
                const Text('No homes yet', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
                const SizedBox(height: 5),
                const Text('Add a home to organize its camera and trusted people.', textAlign: TextAlign.center, style: TextStyle(fontSize: 11, height: 1.4, color: AppColors.textSecondary)),
                const SizedBox(height: 16),
                _PrimaryButton(label: 'Retry initial home setup', icon: Icons.refresh_rounded, onPressed: () => homes.retryInitialHomeSetup(auth.token)),
                const SizedBox(height: 8),
                _PrimaryButton(label: 'Add a home', icon: Icons.add_rounded, onPressed: () => Navigator.of(context).pushNamed(AppRoutes.addHome)),
              ]))
            else ...homes.homes.map((home) {
              final isSelected = home.id == homes.currentHome?.id;
              final subline = home.address?.trim().isNotEmpty == true ? home.address!.trim() : (isSelected ? 'Primary location' : 'Security location');
              return Container(
                margin: const EdgeInsets.only(bottom: 9),
                decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(17), border: Border.all(color: isSelected ? const Color(0xFF80A795) : AppColors.border, width: isSelected ? 1.4 : 1)),
                child: Column(children: [
                  InkWell(
                    borderRadius: BorderRadius.circular(17),
                    onTap: () => homes.selectHome(home, auth.token),
                    child: Padding(padding: const EdgeInsets.fromLTRB(12, 12, 12, 9), child: Row(children: [
                      Container(width: 40, height: 40, decoration: BoxDecoration(color: isSelected ? const Color(0xFFEAF1E8) : const Color(0xFFF1EEE5), borderRadius: BorderRadius.circular(11)), child: Icon(isSelected ? Icons.home_outlined : Icons.apartment_rounded, color: isSelected ? AppColors.forest : const Color(0xFF80765D), size: 18)),
                      const SizedBox(width: 10),
                      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(home.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textPrimary)), const SizedBox(height: 3), Text(subline, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9, color: AppColors.textSecondary))])),
                      if (isSelected) Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6), decoration: BoxDecoration(color: AppColors.lime, borderRadius: BorderRadius.circular(20)), child: const Text('ACTIVE', style: TextStyle(color: AppColors.emeraldInk, fontSize: 8, fontWeight: FontWeight.w800, letterSpacing: .4)))
                      else const Icon(Icons.chevron_right_rounded, size: 18, color: AppColors.textMuted),
                    ])),
                  ),
                  const Divider(height: 1, indent: 12, endIndent: 12, color: AppColors.border),
                  Padding(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7), child: Row(children: [
                    const Icon(Icons.people_outline_rounded, size: 13, color: AppColors.textSecondary),
                    const SizedBox(width: 5),
                    const Expanded(child: Text('Security location', style: TextStyle(fontSize: 9, color: AppColors.textSecondary))),
                    TextButton(onPressed: () => editHome(home), style: TextButton.styleFrom(minimumSize: const Size(0, 28), padding: const EdgeInsets.symmetric(horizontal: 6), tapTargetSize: MaterialTapTargetSize.shrinkWrap, foregroundColor: AppColors.textSecondary), child: const Text('Edit', style: TextStyle(fontSize: 9))),
                    TextButton(onPressed: () => openMembers(home), style: TextButton.styleFrom(minimumSize: const Size(0, 28), padding: const EdgeInsets.symmetric(horizontal: 6), tapTargetSize: MaterialTapTargetSize.shrinkWrap, foregroundColor: AppColors.textSecondary), child: const Text('View people', style: TextStyle(fontSize: 9))),
                    TextButton.icon(onPressed: () => openHome(home), icon: const Icon(Icons.arrow_forward_rounded, size: 11), label: const Text('Open home', style: TextStyle(fontSize: 9)), style: TextButton.styleFrom(minimumSize: const Size(0, 28), padding: const EdgeInsets.only(left: 4), tapTargetSize: MaterialTapTargetSize.shrinkWrap, foregroundColor: AppColors.forest)),
                  ])),
                ]),
              );
            }),
            if (homes.homes.isNotEmpty) ...[
              const SizedBox(height: 2),
              _PrimaryButton(label: 'Add a home', icon: Icons.add_rounded, onPressed: () => Navigator.of(context).pushNamed(AppRoutes.addHome)),
              const SizedBox(height: 10),
              const Text('Each home has its own camera feed, activity, and trusted people.', style: TextStyle(fontSize: 10, height: 1.4, color: AppColors.textSecondary)),
            ],
          ],
        ),
      ),
      bottomNavigationBar: const FloatingCapsuleNavigation(selectedIndex: 2),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onPressed;
  const _PrimaryButton({required this.label, required this.icon, required this.onPressed});
  @override Widget build(BuildContext context) => SizedBox(height: 40, child: ElevatedButton.icon(onPressed: onPressed, icon: Icon(icon, size: 14), label: Text(label, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700)), style: ElevatedButton.styleFrom(backgroundColor: AppColors.emeraldInk, foregroundColor: AppColors.white, minimumSize: const Size.fromHeight(40), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)))));
}
