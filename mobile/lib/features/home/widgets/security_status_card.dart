import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/providers/home_provider.dart';

class SecurityStatusCard extends StatelessWidget {
  final String homeName;
  final SecurityStatusState status;
  final int eventCount;

  const SecurityStatusCard({super.key, required this.homeName, required this.status, this.eventCount = 0});

  @override
  Widget build(BuildContext context) {
    final isSecure = status == SecurityStatusState.secure;
    final isOffline = status == SecurityStatusState.offline;
    final title = switch (status) {
      SecurityStatusState.secure => 'Your home is protected',
      SecurityStatusState.alert => 'Security alert detected',
      SecurityStatusState.unknownActivity => 'Motion activity detected',
      SecurityStatusState.offline => 'Security system offline',
    };
    final subtitle = switch (status) {
      SecurityStatusState.secure => 'All systems are operating normally',
      SecurityStatusState.alert => 'Review recent activity for details',
      SecurityStatusState.unknownActivity => '$eventCount recent security event${eventCount == 1 ? '' : 's'}',
      SecurityStatusState.offline => 'Backend connection is unavailable',
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 12),
      decoration: BoxDecoration(
        color: isSecure ? AppColors.emeraldInk : (isOffline ? AppColors.surfaceSoft : const Color(0xFF674328)),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(children: [
        Container(width: 34, height: 34, decoration: BoxDecoration(color: AppColors.white.withValues(alpha: .12), borderRadius: BorderRadius.circular(11)), child: Icon(isSecure ? Icons.shield_outlined : (isOffline ? Icons.wifi_off_rounded : Icons.warning_amber_rounded), size: 18, color: isOffline ? AppColors.textSecondary : AppColors.lime)),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: isOffline ? AppColors.textPrimary : AppColors.white, fontSize: 12, fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: isOffline ? AppColors.textSecondary : const Color(0xFFD4E2D9), fontSize: 10)),
        ])),
        const SizedBox(width: 8),
        Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7), decoration: BoxDecoration(color: isSecure ? AppColors.lime : (isOffline ? AppColors.border : AppColors.champagne), borderRadius: BorderRadius.circular(20)), child: Text(isSecure ? 'SECURE' : (isOffline ? 'OFFLINE' : 'REVIEW'), style: const TextStyle(color: AppColors.emeraldInk, fontSize: 8, fontWeight: FontWeight.w800, letterSpacing: .4))),
      ]),
    );
  }
}
