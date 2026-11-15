import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/core/network/mjpeg_stream_service.dart';
import 'package:mobile/features/home/provider/camera_stream_provider.dart';

class LiveCameraPreview extends StatelessWidget {
  final bool isBackendConnected;
  final String? homeId;
  final String? accessToken;
  final Future<void> Function()? onRetryConnection;

  const LiveCameraPreview({
    super.key,
    required this.isBackendConnected,
    required this.homeId,
    required this.accessToken,
    this.onRetryConnection,
  });

  @override
  Widget build(BuildContext context) {
    final camera = context.watch<CameraStreamProvider>();
    final service = camera.service;
    return ClipRRect(
      borderRadius: BorderRadius.circular(17),
      child: AspectRatio(
        aspectRatio: 1.9,
        child: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: RadialGradient(
              center: Alignment(.18, -.3),
              radius: 1.2,
              colors: [Color(0xFF344A40), Color(0xFF17261F), Color(0xFF101815)],
            ),
          ),
          child: Stack(
            children: [
              Positioned.fill(
                child: !isBackendConnected
                    ? _buildOfflinePlaceholder(context, camera)
                    : ValueListenableBuilder<CameraStreamStatus>(
                        valueListenable: camera.statusNotifier,
                        builder: (context, status, _) {
                          if (status == CameraStreamStatus.connecting) {
                            return _buildConnectingPlaceholder();
                          }
                          if (status == CameraStreamStatus.error) {
                            return _buildErrorPlaceholder(camera);
                          }
                          return StreamBuilder<Uint8List>(
                            stream: service.frameStream,
                            builder: (context, snapshot) {
                              if (snapshot.hasData &&
                                  snapshot.data != null &&
                                  snapshot.data!.isNotEmpty) {
                                return Image.memory(
                                  snapshot.data!,
                                  fit: BoxFit.cover,
                                  gaplessPlayback: true,
                                  errorBuilder: (_, _, _) =>
                                      _buildErrorPlaceholder(camera),
                                );
                              }
                              return _buildConnectingPlaceholder();
                            },
                          );
                        },
                      ),
              ),
              Positioned.fill(
                child: IgnorePointer(
                  child: CustomPaint(painter: _CameraGridPainter()),
                ),
              ),
              Positioned(
                top: 11,
                left: 11,
                right: 11,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Front entrance',
                      style: TextStyle(
                        color: AppColors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    ValueListenableBuilder<CameraStreamStatus>(
                      valueListenable: camera.statusNotifier,
                      builder: (context, status, _) {
                        final live =
                            isBackendConnected &&
                            status == CameraStreamStatus.streaming;
                        final label = !isBackendConnected
                            ? 'OFFLINE'
                            : (live
                                  ? 'LIVE'
                                  : (status == CameraStreamStatus.connecting
                                        ? 'CONNECTING'
                                        : 'LIVE'));
                        return _StatusBadge(label: label, isLive: live);
                      },
                    ),
                  ],
                ),
              ),
              Positioned(
                left: 12,
                right: 12,
                bottom: 10,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Icon(
                          isBackendConnected
                              ? Icons.wifi_rounded
                              : Icons.wifi_off_rounded,
                          size: 12,
                          color: const Color(0xFFD5E1D8).withValues(alpha: .85),
                        ),
                        const SizedBox(width: 5),
                        Text(
                          camera.videoDiagnostic ??
                              (isBackendConnected
                                  ? 'Camera connected'
                                  : 'Camera unavailable'),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Color(0xFFD5E1D8),
                            fontSize: 8,
                          ),
                        ),
                      ],
                    ),
                    const Text(
                      'HD',
                      style: TextStyle(
                        color: Color(0xFFD5E1D8),
                        fontSize: 8,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConnectingPlaceholder() => const Center(
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        SizedBox(
          width: 22,
          height: 22,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(AppColors.lime),
          ),
        ),
        SizedBox(height: 8),
        Text(
          'Waiting for camera stream',
          style: TextStyle(color: Color(0xFFD7E5DB), fontSize: 9),
        ),
      ],
    ),
  );

  Widget _buildOfflinePlaceholder(
    BuildContext context,
    CameraStreamProvider camera,
  ) => Center(
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(
          Icons.videocam_off_outlined,
          color: AppColors.textMuted,
          size: 24,
        ),
        const SizedBox(height: 5),
        const Text(
          'Backend offline',
          style: TextStyle(
            color: AppColors.white,
            fontSize: 10,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 5),
        OutlinedButton.icon(
          onPressed: homeId == null || accessToken == null
              ? null
              : () async {
                  await onRetryConnection?.call();
                  camera.connect(homeId, accessToken, force: true);
                },
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.white,
            side: const BorderSide(color: Color(0xFF8B9B91)),
            padding: const EdgeInsets.symmetric(horizontal: 10),
            minimumSize: const Size(0, 28),
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          icon: const Icon(Icons.refresh_rounded, size: 12),
          label: const Text('Retry', style: TextStyle(fontSize: 9)),
        ),
      ],
    ),
  );

  Widget _buildErrorPlaceholder(CameraStreamProvider camera) => Center(
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(
          Icons.signal_wifi_connected_no_internet_4_rounded,
          color: AppColors.textMuted,
          size: 24,
        ),
        const SizedBox(height: 6),
        const Text(
          'Camera stream unavailable',
          style: TextStyle(
            color: AppColors.white,
            fontSize: 10,
            fontWeight: FontWeight.w600,
          ),
        ),
        TextButton.icon(
          onPressed: camera.retry,
          style: TextButton.styleFrom(
            foregroundColor: AppColors.lime,
            minimumSize: const Size(0, 28),
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          icon: const Icon(Icons.refresh_rounded, size: 12),
          label: const Text('Retry stream', style: TextStyle(fontSize: 9)),
        ),
      ],
    ),
  );
}

class _StatusBadge extends StatelessWidget {
  final String label;
  final bool isLive;
  const _StatusBadge({required this.label, required this.isLive});
  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(30),
    child: BackdropFilter(
      filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        color: AppColors.emeraldInk.withValues(alpha: .78),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 5,
              height: 5,
              decoration: BoxDecoration(
                color: isLive ? const Color(0xFF85DC9B) : AppColors.textMuted,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(
                color: Color(0xFFDDF3E4),
                fontSize: 8,
                fontWeight: FontWeight.w700,
                letterSpacing: .4,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class _CameraGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFB8D0C4).withValues(alpha: .055)
      ..strokeWidth = 0.6;
    for (double x = 0; x <= size.width; x += 38) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y <= size.height; y += 38) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
