import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/features/home/provider/alerts_provider.dart';
import 'package:mobile/models/alert_model.dart';
import 'package:mobile/core/config/api_config.dart';

class AlertsSection extends StatelessWidget {
  final String? homeId;
  final String? token;
  const AlertsSection({super.key, required this.homeId, required this.token});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AlertsProvider>();
    return Card(
      color: AppColors.surface,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Security Alerts',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                if (provider.unreadCount > 0)
                  Text('${provider.unreadCount} unread'),
                IconButton(
                  tooltip: 'Refresh alerts',
                  onPressed: provider.isLoading
                      ? null
                      : () => provider.load(homeId, token),
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            if (provider.isLoading && provider.alerts.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(12),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (provider.error != null && provider.alerts.isEmpty)
              Text(
                provider.error!,
                style: const TextStyle(color: AppColors.textSecondary),
              )
            else if (provider.alerts.isEmpty)
              const Text(
                'No recent alerts.',
                style: TextStyle(color: AppColors.textSecondary),
              )
            else
              ...provider.alerts
                  .take(5)
                  .map(
                    (alert) =>
                        _AlertTile(alert: alert, token: token, homeId: homeId),
                  ),
          ],
        ),
      ),
    );
  }
}

class _AlertTile extends StatelessWidget {
  final AlertModel alert;
  final String? token;
  final String? homeId;
  const _AlertTile({
    required this.alert,
    required this.token,
    required this.homeId,
  });

  @override
  Widget build(BuildContext context) => Column(
    children: [
      ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(
          alert.isRead
              ? Icons.notifications_none
              : Icons.notification_important_outlined,
        ),
        title: Text(alert.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text(
          alert.message,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: alert.isRead
            ? null
            : TextButton(
                onPressed: () => context.read<AlertsProvider>().markRead(
                  alert.id,
                  true,
                  token,
                ),
                child: const Text('Read'),
              ),
      ),
      if (alert.imagePath != null &&
          alert.imagePath!.isNotEmpty &&
          homeId != null &&
          token != null &&
          !alert.imagePath!.contains('/') &&
          !alert.imagePath!.contains('\\'))
        Align(
          alignment: Alignment.centerLeft,
          child: SizedBox(
            width: 150,
            height: 84,
            child: Image.network(
              '${ApiConfig.baseUrl}/video/homes/$homeId/evidence/${Uri.encodeComponent(alert.imagePath!)}',
              headers: {'Authorization': 'Bearer $token'},
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => const SizedBox.shrink(),
            ),
          ),
        ),
    ],
  );
}
