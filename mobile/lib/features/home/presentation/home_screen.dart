import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/features/home/provider/alerts_provider.dart';
import 'package:mobile/features/home/provider/camera_stream_provider.dart';
import 'package:mobile/features/home/provider/face_occlusion_provider.dart';
import 'package:mobile/features/home/widgets/face_analysis_panel.dart';
import 'package:mobile/features/home/widgets/live_camera_preview.dart';
import 'package:mobile/features/home/widgets/recent_activity.dart';
import 'package:mobile/features/home/widgets/security_status_card.dart';
import 'package:mobile/features/members/provider/members_provider.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';
import 'package:mobile/core/widgets/floating_capsule_navigation.dart';
import 'package:mobile/features/voice/provider/voice_provider.dart';
import 'package:mobile/features/voice/widgets/voice_control_button.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with WidgetsBindingObserver, RouteAware {
  bool _screenActive = true;
  late FaceOcclusionProvider _faceOcclusionProvider;
  late VoiceProvider _voiceProvider;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _faceOcclusionProvider = context.read<FaceOcclusionProvider>();
    _voiceProvider = context.read<VoiceProvider>();
    final route = ModalRoute.of(context);
    if (route != null) AppRoutes.observer.subscribe(this, route);
  }

  @override
  void didPushNext() {
    _screenActive = false;
    _faceOcclusionProvider.stopPolling();
  }

  @override
  void didPopNext() {
    _screenActive = true;
    final auth = context.read<AuthProvider>();
    final home = context.read<HomeProvider>();
    context.read<FaceOcclusionProvider>().startPolling(
      home.currentHome?.id,
      auth.token,
    );
  }

  void _syncFaceOcclusion(String? homeId, String? token) {
    if (!_screenActive) return;
    context.read<FaceOcclusionProvider>().startPolling(homeId, token);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _screenActive = state == AppLifecycleState.resumed;
    final provider = context.read<FaceOcclusionProvider>();
    if (_screenActive) {
      final auth = context.read<AuthProvider>();
      final home = context.read<HomeProvider>();
      provider.startPolling(home.currentHome?.id, auth.token);
    } else {
      provider.stopPolling();
      unawaited(context.read<VoiceProvider>().cancelRecording());
    }
  }

  @override
  void dispose() {
    AppRoutes.observer.unsubscribe(this);
    WidgetsBinding.instance.removeObserver(this);
    _faceOcclusionProvider.stopPolling();
    unawaited(_voiceProvider.cancelRecording());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final home = context.watch<HomeProvider>();
    final alerts = context.read<AlertsProvider>();
    final userName = auth.currentUser?.name.trim() ?? '';
    final firstName = userName.isEmpty ? 'there' : userName.split(' ').first;
    final now = DateTime.now();
    const weekdays = [
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
      'Sunday',
    ];
    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    final dateLabel =
        '${weekdays[now.weekday - 1]}, ${months[now.month - 1]} ${now.day}';
    final greeting = now.hour < 12
        ? 'Good morning,'
        : (now.hour < 17 ? 'Good afternoon,' : 'Good evening,');

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!home.dashboardLoadStarted) {
        await home.initializeDashboard(auth.token);
      }
      if (context.mounted) {
        _syncFaceOcclusion(home.currentHome?.id, auth.token);
        if (home.isBackendConnected) {
          home.startRealtimeUpdates(home.currentHome?.id, auth.token);
          context.read<CameraStreamProvider>().connect(
            home.currentHome?.id,
            auth.token,
          );
        } else {
          home.stopRealtimeUpdates();
          context.read<CameraStreamProvider>().clearSessionData();
        }
        final alertProvider = context.read<AlertsProvider>();
        if (home.isBackendConnected) {
          alertProvider.startRealtimeUpdates(home.currentHome?.id, auth.token);
        } else {
          alertProvider.stopRealtimeUpdates();
        }
        alertProvider.load(home.currentHome?.id, auth.token);
      }
    });

    Future<void> logout() async {
      final authProvider = context.read<AuthProvider>();
      final homes = context.read<HomeProvider>();
      final alertProvider = context.read<AlertsProvider>();
      final camera = context.read<CameraStreamProvider>();
      final members = context.read<MembersProvider>();
      await authProvider.logout();
      homes.clearSessionData();
      alertProvider.clearSessionData();
      await camera.clearSessionData();
      await members.clearSessionData();
      if (!context.mounted) return;
      Navigator.of(context).pushReplacementNamed(AppRoutes.login);
    }

    Future<void> pairCamera() async {
      final selectedHome = home.currentHome;
      final token = auth.token;
      if (selectedHome == null || token == null) return;
      try {
        final pairingCode = await home.generatePairingCode(
          token,
          selectedHome.id,
        );
        if (!context.mounted) return;
        await showDialog<void>(
          context: context,
          builder: (dialogContext) {
            final expiry = pairingCode.expiresAt.toLocal();
            final expiryDate = MaterialLocalizations.of(
              dialogContext,
            ).formatMediumDate(expiry);
            final expiryTime = MaterialLocalizations.of(
              dialogContext,
            ).formatTimeOfDay(TimeOfDay.fromDateTime(expiry));
            return AlertDialog(
              title: const Text('Pair a camera'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Enter this code on the desktop for ${selectedHome.name}.',
                  ),
                  const SizedBox(height: 16),
                  Center(
                    child: SelectableText(
                      pairingCode.code,
                      style: Theme.of(dialogContext).textTheme.headlineMedium
                          ?.copyWith(
                            fontWeight: FontWeight.w800,
                            letterSpacing: 3,
                          ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text('Expires $expiryDate at $expiryTime'),
                  Text(
                    'About ${(pairingCode.ttlSeconds / 60).ceil()} minutes remaining.',
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Done'),
                ),
              ],
            );
          },
        );
      } catch (_) {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Could not create a pairing code. Check your connection and home access.',
            ),
          ),
        );
      }
    }

    // TEMP DEBUG: remove this action with the provider diagnostic after verification.
    Future<void> checkVideoStatus() async {
      final camera = context.read<CameraStreamProvider>();
      await camera.debugCheckVideoStatus(home.currentHome?.id, auth.token);
      if (!context.mounted) return;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Video status'),
          content: Text(
            camera.debugVideoStatusMessage ?? 'Video status unavailable',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.emeraldInk,
          backgroundColor: AppColors.surface,
          onRefresh: () async {
            await home.refresh(auth.token);
            await alerts.load(home.currentHome?.id, auth.token, force: true);
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(22, 8, 22, 24),
            children: [
              if (home.errorMessage != null)
                Container(
                  margin: const EdgeInsets.fromLTRB(18, 8, 18, 0),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.champagneSoft,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        home.errorMessage!,
                        style: const TextStyle(
                          color: AppColors.error,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(height: 6),
                      TextButton(
                        onPressed: () => home.retryInitialHomeSetup(auth.token),
                        child: const Text('Retry home setup'),
                      ),
                    ],
                  ),
                ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'OTTO',
                    style: TextStyle(
                      color: AppColors.emeraldInk,
                      fontSize: 15,
                      letterSpacing: 3,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  InkWell(
                    borderRadius: BorderRadius.circular(24),
                    onTap: () =>
                        Navigator.of(context).pushNamed(AppRoutes.profile),
                    child: CircleAvatar(
                      radius: 18,
                      backgroundColor: AppColors.champagne,
                      foregroundColor: AppColors.emeraldInk,
                      child: Text(
                        userName.isNotEmpty ? userName[0].toUpperCase() : 'H',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 17),
              Text(
                dateLabel.toUpperCase(),
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                '$greeting\n$firstName',
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 26,
                  height: 1.08,
                  letterSpacing: -.8,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 15),
              InkWell(
                onTap: () => Navigator.of(context).pushNamed(AppRoutes.homes),
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 11,
                    vertical: 9,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 34,
                        height: 34,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEAF1E8),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(
                          Icons.home_outlined,
                          color: AppColors.forest,
                          size: 17,
                        ),
                      ),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              home.currentHome?.name ?? 'Select or add a home',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 2),
                            const Text(
                              'Home dashboard',
                              style: TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 9,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Tooltip(
                        message: home.isBackendConnected
                            ? 'FastAPI connected. Tap to refresh.'
                            : 'Backend offline. Tap to retry.',
                        child: InkWell(
                          onTap: () => home.loadHomeData(auth.token),
                          borderRadius: BorderRadius.circular(20),
                          child: Padding(
                            padding: const EdgeInsets.all(7),
                            child: Icon(
                              Icons.circle,
                              size: 8,
                              color: home.isBackendConnected
                                  ? AppColors.success
                                  : AppColors.error,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 3),
                      const Icon(
                        Icons.keyboard_arrow_down_rounded,
                        color: AppColors.textSecondary,
                        size: 17,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SecurityStatusCard(
                homeName: home.currentHome?.name ?? 'Home',
                status: home.securityStatus,
                eventCount: home.recentEvents.length,
              ),
              const SizedBox(height: 17),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Live camera',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextButton.icon(
                        onPressed:
                            home.currentHome == null || auth.token == null
                            ? null
                            : pairCamera,
                        icon: const Icon(Icons.add_link_rounded, size: 14),
                        label: const Text(
                          'Pair Camera',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        style: TextButton.styleFrom(
                          foregroundColor: AppColors.forest,
                          padding: const EdgeInsets.symmetric(horizontal: 6),
                          minimumSize: const Size(0, 28),
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                        ),
                        if (kDebugMode)
                          TextButton.icon(
                            onPressed: checkVideoStatus,
                            icon: const Icon(Icons.health_and_safety_outlined, size: 14),
                            label: const Text(
                              'Debug status',
                              style: TextStyle(
                                fontSize: 9,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            style: TextButton.styleFrom(
                              foregroundColor: AppColors.forest,
                              padding: const EdgeInsets.symmetric(horizontal: 6),
                              minimumSize: const Size(0, 28),
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                          ),
                        TextButton.icon(
                        onPressed: () =>
                            Navigator.of(context).pushNamed(AppRoutes.homes),
                        icon: const Icon(Icons.arrow_forward_rounded, size: 12),
                        label: const Text(
                          'View all',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        style: TextButton.styleFrom(
                          foregroundColor: AppColors.forest,
                          padding: EdgeInsets.zero,
                          minimumSize: const Size(0, 28),
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 7),
              LiveCameraPreview(
                isBackendConnected: home.isBackendConnected,
                homeId: home.currentHome?.id,
                accessToken: auth.token,
                onRetryConnection: () async => home.loadHomeData(auth.token),
              ),
              const SizedBox(height: 16),
              const FaceAnalysisPanel(),
              const SizedBox(height: 16),
              const VoiceControlButton(),
              const SizedBox(height: 16),
              RecentActivity(
                events: home.recentEvents,
                isLoading: home.isLoading,
                isConnected: home.isBackendConnected,
                homeId: home.currentHome?.id,
                token: auth.token,
                onSeeAll: () =>
                    Navigator.of(context).pushNamed(AppRoutes.alerts),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: const FloatingCapsuleNavigation(selectedIndex: 0),
    );
  }
}
