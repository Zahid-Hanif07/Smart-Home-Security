import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/features/home/widgets/activity_item.dart';
import 'package:mobile/models/security_log_model.dart';

class RecentActivity extends StatelessWidget {
  final List<SecurityLogModel> events;
  final bool isLoading;
  final bool isConnected;
  final String? homeId;
  final String? token;
  final VoidCallback? onSeeAll;

  const RecentActivity({super.key, required this.events, required this.isLoading, required this.isConnected, this.homeId, this.token, this.onSeeAll});

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
      const Text('Recent activity', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
      TextButton.icon(onPressed: onSeeAll, icon: const Icon(Icons.arrow_forward_rounded, size: 12), label: const Text('See all', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w600)), style: TextButton.styleFrom(foregroundColor: AppColors.forest, padding: EdgeInsets.zero, minimumSize: const Size(0, 28), tapTargetSize: MaterialTapTargetSize.shrinkWrap)),
    ]),
    const Divider(height: 8, color: AppColors.border),
    if (!isConnected)
      _empty(Icons.wifi_off_rounded, 'Backend disconnected', 'Reconnect to FastAPI to view recent activity.')
    else if (isLoading && events.isEmpty)
      const Padding(padding: EdgeInsets.symmetric(vertical: 18), child: Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.emeraldInk))))
    else if (events.isEmpty)
      _empty(Icons.shield_outlined, 'No recent activity', 'Your home security events will appear here.')
    else
      ...events.take(3).map((event) => ActivityItem(log: event, homeId: homeId, token: token)),
  ]);

  Widget _empty(IconData icon, String title, String message) => Padding(padding: const EdgeInsets.symmetric(vertical: 14), child: Row(children: [
    Container(width: 32, height: 32, decoration: BoxDecoration(color: AppColors.emeraldSoft, borderRadius: BorderRadius.circular(10)), child: Icon(icon, size: 16, color: AppColors.forest)),
    const SizedBox(width: 10),
    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.textPrimary)), const SizedBox(height: 2), Text(message, style: const TextStyle(fontSize: 9, color: AppColors.textSecondary))])),
  ]));
}
