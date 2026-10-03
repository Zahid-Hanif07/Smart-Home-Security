import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/core/network/mjpeg_stream_service.dart';

class LiveCameraPreview extends StatelessWidget {
  final bool isBackendConnected;
  final VoidCallback? onRetryConnection;

  const LiveCameraPreview({
    super.key,
    required this.isBackendConnected,
    this.onRetryConnection,
  });

  String get _streamUrl => '${ApiConfig.baseUrl}${ApiConfig.videoStreamEndpoint}';

  @override
  Widget build(BuildContext context) {
    final streamService = MjpegStreamService();

    // Auto-trigger stream connection if backend online and stream idle
    if (isBackendConnected && streamService.status == CameraStreamStatus.idle) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        streamService.startStream(_streamUrl);
      });
    }

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
        border: Border.all(color: AppColors.border, width: 1.0),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Bar
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.sm + 4,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.videocam_outlined,
                      size: 18,
                      color: AppColors.black,
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      'Live Camera View',
                      style: AppTextStyles.label,
                    ),
                  ],
                ),
                ValueListenableBuilder<CameraStreamStatus>(
                  valueListenable: streamService.statusNotifier,
                  builder: (context, status, _) {
                    if (!isBackendConnected) {
                      return _buildStatusBadge('OFFLINE', AppColors.textMuted, AppColors.surfaceSoft);
                    }
                    switch (status) {
                      case CameraStreamStatus.streaming:
                        return _buildStatusBadge('LIVE', AppColors.emeraldInk, AppColors.champagne);
                      case CameraStreamStatus.connecting:
                        return _buildStatusBadge('CONNECTING', AppColors.warning, AppColors.surfaceSoft);
                      case CameraStreamStatus.error:
                      case CameraStreamStatus.idle:
                        return _buildStatusBadge('UNAVAILABLE', AppColors.textMuted, AppColors.surfaceSoft);
                    }
                  },
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: AppColors.borderSubtle),

          // Camera Viewport
          AspectRatio(
            aspectRatio: 16 / 9,
            child: Container(
              color: AppColors.black,
              child: !isBackendConnected
                  ? _buildOfflinePlaceholder(context, streamService)
                  : ValueListenableBuilder<CameraStreamStatus>(
                      valueListenable: streamService.statusNotifier,
                      builder: (context, status, _) {
                        if (status == CameraStreamStatus.connecting) {
                          return _buildConnectingPlaceholder();
                        } else if (status == CameraStreamStatus.error) {
                          return _buildErrorPlaceholder(context, streamService);
                        }

                        return StreamBuilder<Uint8List>(
                          stream: streamService.frameStream,
                          builder: (context, snapshot) {
                            if (snapshot.hasData && snapshot.data != null && snapshot.data!.isNotEmpty) {
                              return Image.memory(
                                snapshot.data!,
                                fit: BoxFit.cover,
                                gaplessPlayback: true,
                                errorBuilder: (context, error, stackTrace) =>
                                    _buildErrorPlaceholder(context, streamService),
                              );
                            }
                            return _buildConnectingPlaceholder();
                          },
                        );
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge(String text, Color textColor, Color bgColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: 3),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(AppSpacing.radiusPill),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: textColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            text,
            style: AppTextStyles.caption.copyWith(
              color: textColor,
              fontWeight: FontWeight.w700,
              fontSize: 10,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConnectingPlaceholder() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.white),
            ),
          ),
          SizedBox(height: AppSpacing.sm),
          Text(
            'Connecting camera feed...',
            style: TextStyle(color: AppColors.textMuted, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildOfflinePlaceholder(BuildContext context, MjpegStreamService streamService) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.videocam_off_outlined, color: AppColors.textMuted, size: 32),
          const SizedBox(height: AppSpacing.sm),
          const Text(
            'Backend Offline',
            style: TextStyle(color: AppColors.white, fontSize: 14, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: AppSpacing.xs),
          const Text(
            'Connect FastAPI backend to view stream',
            style: TextStyle(color: AppColors.textMuted, fontSize: 12),
          ),
          const SizedBox(height: AppSpacing.md),
          OutlinedButton.icon(
            onPressed: () {
              if (onRetryConnection != null) {
                onRetryConnection!();
              }
              streamService.startStream(_streamUrl);
            },
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.white,
              side: const BorderSide(color: AppColors.textMuted),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              minimumSize: const Size(0, 36),
            ),
            icon: const Icon(Icons.refresh_rounded, size: 16),
            label: const Text('Retry Connection', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorPlaceholder(BuildContext context, MjpegStreamService streamService) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.signal_cellular_connected_no_internet_4_bar, color: AppColors.textMuted, size: 32),
          const SizedBox(height: AppSpacing.sm),
          const Text(
            'Camera Feed Unavailable',
            style: TextStyle(color: AppColors.white, fontSize: 14, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: AppSpacing.xs),
          const Text(
            'Verify webcam feed on FastAPI /video/stream',
            style: TextStyle(color: AppColors.textMuted, fontSize: 12),
          ),
          const SizedBox(height: AppSpacing.md),
          OutlinedButton.icon(
            onPressed: () {
              streamService.startStream(_streamUrl);
            },
            style: OutlinedButton.styleFrom(
              foregroundColor: AppColors.white,
              side: const BorderSide(color: AppColors.textMuted),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              minimumSize: const Size(0, 36),
            ),
            icon: const Icon(Icons.refresh_rounded, size: 16),
            label: const Text('Retry Stream', style: TextStyle(fontSize: 13)),
          ),
        ],
      ),
    );
  }
}
