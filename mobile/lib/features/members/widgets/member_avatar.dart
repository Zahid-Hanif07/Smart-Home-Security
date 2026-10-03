import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';

class MemberAvatar extends StatelessWidget {
  final String name;
  final double size;
  final bool hasRegisteredFace;

  const MemberAvatar({
    super.key,
    required this.name,
    this.size = 48.0,
    this.hasRegisteredFace = false,
  });

  String get _initials {
    if (name.trim().isEmpty) return '?';
    final parts = name.trim().split(' ');
    if (parts.length > 1) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return parts[0][0].toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: hasRegisteredFace ? AppColors.champagne : AppColors.surfaceSoft,
        shape: BoxShape.circle,
        border: Border.all(
          color: hasRegisteredFace ? AppColors.emeraldInk : AppColors.border,
          width: 1.5,
        ),
      ),
      child: Center(
        child: Text(
          _initials,
          style: TextStyle(
            color: hasRegisteredFace ? AppColors.black : AppColors.textSecondary,
            fontWeight: FontWeight.w700,
            fontSize: size * 0.38,
          ),
        ),
      ),
    );
  }
}
