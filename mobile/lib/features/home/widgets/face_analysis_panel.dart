import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/models/face_occlusion_diagnostic_model.dart';
import 'package:mobile/features/home/provider/face_occlusion_provider.dart';

class FaceAnalysisPanel extends StatelessWidget {
  const FaceAnalysisPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<FaceOcclusionProvider>();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(17),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Face analysis',
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _stateLabel(provider.state),
            style: const TextStyle(
              color: AppColors.forest,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (provider.state == FaceOcclusionViewState.loading) ...[
            const SizedBox(height: 8),
            const LinearProgressIndicator(minHeight: 2),
          ],
          if (provider.errorMessage != null) ...[
            const SizedBox(height: 5),
            Text(
              provider.errorMessage!,
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 10),
            ),
          ],
          ...provider.results.map(_resultRow),
        ],
      ),
    );
  }

  Widget _resultRow(FaceOcclusionDiagnostic result) {
    final ratio = result.visibleRatio == null
        ? '—'
        : '${(result.visibleRatio! * 100).toStringAsFixed(1)}% visible';
    final inference = result.inferenceMs == null
        ? '—'
        : '${result.inferenceMs!.toStringAsFixed(1)} ms';
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Text(
        'Face ${result.faceIndex + 1}  •  $ratio  •  $inference  •  ${result.freshness.toUpperCase()}',
        style: const TextStyle(color: AppColors.textSecondary, fontSize: 10),
      ),
    );
  }

  String _stateLabel(FaceOcclusionViewState state) => switch (state) {
    FaceOcclusionViewState.idle => 'WAITING',
    FaceOcclusionViewState.loading => 'LOADING',
    FaceOcclusionViewState.waiting => 'WAITING — no diagnostic result',
    FaceOcclusionViewState.analyzed => 'ANALYZED',
    FaceOcclusionViewState.uncertain => 'UNCERTAIN',
    FaceOcclusionViewState.unavailable => 'UNAVAILABLE',
    FaceOcclusionViewState.failed => 'FAILED',
    FaceOcclusionViewState.stale => 'STALE',
    FaceOcclusionViewState.noFace => 'NO FACE',
    FaceOcclusionViewState.error => 'NETWORK/API ERROR',
  };
}
