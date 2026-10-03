import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';

/// Subtle Translucent Blur Surface Widget
/// Used with restraint for floating headers, badges, or selective highlight panels.
class SubtleBlurCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final Color? borderColor;
  final Color? backgroundColor;
  final double blurSigma;

  const SubtleBlurCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius = AppSpacing.radiusMd,
    this.borderColor,
    this.backgroundColor,
    this.blurSigma = 10.0,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
          child: Container(
            padding: padding ?? const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: backgroundColor ?? AppColors.surfaceTranslucent,
              borderRadius: BorderRadius.circular(borderRadius),
              border: Border.all(
                color: borderColor ?? AppColors.border,
                width: 1.0,
              ),
            ),
            child: child,
          ),
        ),
      ),
    );
  }
}
