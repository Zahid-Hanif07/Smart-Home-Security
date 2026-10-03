import 'package:flutter/material.dart';

/// Centralized Color System for Smart Home Security
/// FINAL APPROVED PALETTE:
/// - PRIMARY: Emerald Ink (#064E3B)
/// - SECONDARY: Champagne (#F8E7C9)
/// - SUPPORTING: White / Off-white, Neutral Grays, Black / Near-black typography, Subtle blur
class AppColors {
  AppColors._();

  // Primary & Secondary Brand Colors
  static const Color emeraldInk = Color(0xFF064E3B); // Primary Emerald Ink
  static const Color champagne = Color(0xFFF8E7C9); // Secondary Champagne
  static const Color primary = Color(0xFF064E3B);
  static const Color secondary = Color(0xFFF8E7C9);

  // Background & Surfaces (White & Off-White)
  static const Color background = Color(0xFFFAFAFA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceSoft = Color(0xFFF4F4F5);
  static const Color surfaceTranslucent = Color(0xCCFFFFFF); // 80% white for blur

  // Primary Controls & Typography (Black / Near-Black)
  static const Color black = Color(0xFF09090B);
  static const Color textPrimary = Color(0xFF09090B); // Near-black typography
  static const Color textSecondary = Color(0xFF71717A); // Neutral gray
  static const Color textMuted = Color(0xFFA1A1AA); // Light neutral gray

  // Champagne & Emerald Soft Surfaces
  static const Color champagneSoft = Color(0xFFFDF8F0); // Light Champagne tint fill
  static const Color emeraldSoft = Color(0xFFECFDF5); // Light Emerald tint fill
  static const Color champagneHover = Color(0xFFF5DDA6); // Interactive Champagne state

  // Structure & Dividers
  static const Color border = Color(0xFFE4E4E7);
  static const Color borderSubtle = Color(0xFFF4F4F5);

  // Status Indicators (Minimal & Semantic)
  static const Color success = Color(0xFF10B981); // Emerald connected state
  static const Color warning = Color(0xFFF59E0B); // Amber warning
  static const Color error = Color(0xFFEF4444); // Red alert
  static const Color white = Color(0xFFFFFFFF);
}
