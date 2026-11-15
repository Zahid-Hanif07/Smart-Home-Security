import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/core/widgets/floating_capsule_navigation.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.background,
    appBar: AppBar(title: const Text('Settings')),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 22),
      children: const [
        _Eyebrow('MAKE OTTO YOURS'),
        SizedBox(height: 5),
        Text('Settings', style: TextStyle(fontSize: 27, height: 1.1, letterSpacing: -.7, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
        SizedBox(height: 17),
        _SectionTitle('Notifications'),
        _SettingRow(icon: Icons.notifications_active_outlined, title: 'Security alerts', subtitle: 'Important activity at your home', visualToggle: true),
        _SettingRow(icon: Icons.face_retouching_natural_rounded, title: 'Face recognition', subtitle: 'Trusted person activity', visualToggle: true),
        SizedBox(height: 14),
        _SectionTitle('App preferences'),
        _SettingRow(icon: Icons.volume_up_outlined, title: 'Alert sounds', subtitle: 'Sound for urgent notifications', visualToggle: true),
        _SettingRow(icon: Icons.lock_outline_rounded, title: 'Privacy & security', subtitle: 'Review data and permissions', hasChevron: true),
        _SettingRow(icon: Icons.help_outline_rounded, title: 'Help & support', subtitle: 'Get help with OTTO', hasChevron: true),
        SizedBox(height: 14),
        _SectionTitle('Smart home'),
        _SettingRow(icon: Icons.mic_none_rounded, title: 'Voice control', subtitle: 'Appliance controls are coming soon', tag: 'SOON'),
        SizedBox(height: 16),
        Center(child: Text('OTTO Smart Home Security · Version 1.0', style: TextStyle(fontSize: 9, color: AppColors.textMuted))),
      ],
    ),
    bottomNavigationBar: const FloatingCapsuleNavigation(selectedIndex: 3, profileMode: true),
  );
}

class _Eyebrow extends StatelessWidget {
  final String text;
  const _Eyebrow(this.text);
  @override Widget build(BuildContext context) => Text(text, style: const TextStyle(fontSize: 9, letterSpacing: 1.2, fontWeight: FontWeight.w700, color: AppColors.textSecondary));
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);
  @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(left: 1, bottom: 4), child: Text(text, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textPrimary)));
}

class _SettingRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool visualToggle;
  final bool hasChevron;
  final String? tag;
  const _SettingRow({required this.icon, required this.title, required this.subtitle, this.visualToggle = false, this.hasChevron = false, this.tag});

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(vertical: 9),
    decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.border))),
    child: Row(children: [
      Container(width: 30, height: 30, decoration: BoxDecoration(color: AppColors.emeraldSoft, borderRadius: BorderRadius.circular(10)), child: Icon(icon, size: 15, color: AppColors.forest)),
      const SizedBox(width: 9),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.textPrimary)), const SizedBox(height: 2), Text(subtitle, style: const TextStyle(fontSize: 8, color: AppColors.textSecondary))])),
      if (visualToggle) const _SwitchVisual() else if (tag != null) Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4), decoration: BoxDecoration(color: AppColors.champagne, borderRadius: BorderRadius.circular(12)), child: Text(tag!, style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w800, color: AppColors.forest))) else if (hasChevron) const Icon(Icons.chevron_right_rounded, size: 16, color: AppColors.textSecondary),
    ]),
  );
}

class _SwitchVisual extends StatelessWidget {
  const _SwitchVisual();
  @override Widget build(BuildContext context) => Container(width: 30, height: 16, padding: const EdgeInsets.all(2), decoration: BoxDecoration(color: AppColors.emeraldInk, borderRadius: BorderRadius.circular(12)), child: const Align(alignment: Alignment.centerRight, child: CircleAvatar(radius: 6, backgroundColor: AppColors.white)));
}
