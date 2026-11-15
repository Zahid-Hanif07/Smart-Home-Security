import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/core/widgets/floating_capsule_navigation.dart';
import 'package:mobile/features/home/provider/alerts_provider.dart';
import 'package:mobile/features/home/provider/camera_stream_provider.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final homes = context.watch<HomeProvider>();
    final user = auth.currentUser;
    final name = user?.name ?? 'Homeowner';
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'OTTO',
          style: TextStyle(
            letterSpacing: 3,
            fontWeight: FontWeight.w800,
            color: AppColors.emeraldInk,
          ),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 18),
            child: Center(
              child: Text(
                'ACCOUNT',
                style: TextStyle(
                  fontSize: 10,
                  letterSpacing: 1.4,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 10, 20, 24),
        children: [
          const Text(
            'YOUR ACCOUNT',
            style: TextStyle(
              fontSize: 10,
              letterSpacing: 1.2,
              fontWeight: FontWeight.w700,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 5),
          const Text(
            'Profile',
            style: TextStyle(
              fontSize: 28,
              height: 1.15,
              fontWeight: FontWeight.w700,
              letterSpacing: -.7,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.symmetric(vertical: 18),
            decoration: BoxDecoration(
              color: AppColors.surface,
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 38,
                  backgroundColor: AppColors.champagne,
                  foregroundColor: AppColors.emeraldInk,
                  child: Text(
                    name.isNotEmpty ? name[0].toUpperCase() : 'H',
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  name,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 3),
                const Text(
                  'Owner account',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(15),
            decoration: BoxDecoration(
              color: AppColors.surface,
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'PERSONAL INFORMATION',
                  style: TextStyle(
                    fontSize: 10,
                    letterSpacing: 1.1,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 12),
                _InfoLine(label: 'Full name', value: name),
                const Divider(height: 20, color: AppColors.borderSubtle),
                _InfoLine(label: 'Email address', value: user?.email ?? '—'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          _ProfileRow(
            icon: Icons.home_work_outlined,
            title: 'Your homes',
            subtitle:
                '${homes.homes.length} security location${homes.homes.length == 1 ? '' : 's'}',
            onTap: () => Navigator.pushNamed(context, AppRoutes.homes),
          ),
          _ProfileRow(
            icon: Icons.shield_outlined,
            title: 'Security & privacy',
            subtitle: 'Manage your account protection',
            onTap: () => Navigator.pushNamed(context, AppRoutes.settings),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            icon: const Icon(Icons.logout_rounded),
            label: const Text('Sign out'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.textPrimary,
              backgroundColor: AppColors.surfaceSoft,
              side: BorderSide.none,
              minimumSize: const Size.fromHeight(48),
            ),
            onPressed: () async {
              final alerts = context.read<AlertsProvider>();
              final camera = context.read<CameraStreamProvider>();
              final members = context.read<MembersProvider>();
              await auth.logout();
              homes.clearSessionData();
              alerts.clearSessionData();
              await camera.clearSessionData();
              await members.clearSessionData();
              if (!context.mounted) return;
              Navigator.of(context).pushReplacementNamed(AppRoutes.login);
            },
          ),
        ],
      ),
      bottomNavigationBar: const FloatingCapsuleNavigation(
        selectedIndex: 3,
        profileMode: true,
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  final String label, value;
  const _InfoLine({required this.label, required this.value});
  @override
  Widget build(BuildContext context) => Row(
    mainAxisAlignment: MainAxisAlignment.spaceBetween,
    children: [
      Text(
        label,
        style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
      ),
      const SizedBox(width: 12),
      Flexible(
        child: Text(
          value,
          textAlign: TextAlign.right,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
      ),
    ],
  );
}

class _ProfileRow extends StatelessWidget {
  final IconData icon;
  final String title, subtitle;
  final VoidCallback onTap;
  const _ProfileRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });
  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 8),
    child: ListTile(
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: AppColors.champagneSoft,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: AppColors.emeraldInk, size: 20),
      ),
      title: Text(
        title,
        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
      ),
      subtitle: Text(subtitle, style: const TextStyle(fontSize: 11)),
      trailing: const Icon(
        Icons.chevron_right_rounded,
        color: AppColors.textMuted,
      ),
      onTap: onTap,
    ),
  );
}
