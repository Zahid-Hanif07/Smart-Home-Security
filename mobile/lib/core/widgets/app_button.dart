import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_text_styles.dart';

enum AppButtonVariant {
  primary, // Black background, white text
  secondary, // Light Pink background, black text
  outlined, // White background, black text, neutral border
}

class AppButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final AppButtonVariant variant;
  final bool isOutlined; // Backwards compatibility for bool prop
  final IconData? icon;
  final double? height;

  const AppButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.variant = AppButtonVariant.primary,
    this.isOutlined = false,
    this.icon,
    this.height = 52.0,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveVariant = isOutlined ? AppButtonVariant.outlined : variant;

    switch (effectiveVariant) {
      case AppButtonVariant.outlined:
        return OutlinedButton(
          onPressed: isLoading ? null : onPressed,
          style: OutlinedButton.styleFrom(
            minimumSize: Size(double.infinity, height ?? 52.0),
            backgroundColor: AppColors.surface,
            foregroundColor: AppColors.black,
            side: const BorderSide(color: AppColors.border, width: 1.0),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.0,
                    color: AppColors.black,
                  ),
                )
              : _buildButtonChild(AppColors.black),
        );

      case AppButtonVariant.secondary:
        return ElevatedButton(
          onPressed: isLoading ? null : onPressed,
          style: ElevatedButton.styleFrom(
            minimumSize: Size(double.infinity, height ?? 52.0),
            backgroundColor: AppColors.champagne,
            foregroundColor: AppColors.black,
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.0,
                    color: AppColors.black,
                  ),
                )
              : _buildButtonChild(AppColors.black),
        );

      case AppButtonVariant.primary:
        return ElevatedButton(
          onPressed: isLoading ? null : onPressed,
          style: ElevatedButton.styleFrom(
            minimumSize: Size(double.infinity, height ?? 52.0),
            backgroundColor: AppColors.emeraldInk,
            foregroundColor: AppColors.white,
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.0,
                    color: AppColors.white,
                  ),
                )
              : _buildButtonChild(AppColors.white),
        );
    }
  }

  Widget _buildButtonChild(Color textColor) {
    if (icon != null) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: textColor),
          const SizedBox(width: 8),
          Text(
            text,
            style: AppTextStyles.button.copyWith(color: textColor),
          ),
        ],
      );
    }
    return Text(
      text,
      style: AppTextStyles.button.copyWith(color: textColor),
    );
  }
}
