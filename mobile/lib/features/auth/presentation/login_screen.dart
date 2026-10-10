import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/routes/app_routes.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/features/auth/widgets/auth_header.dart';
import 'package:mobile/features/auth/widgets/auth_text_field.dart';
import 'package:mobile/features/auth/widgets/auth_button.dart';
import 'package:mobile/providers/auth_provider.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  Future<void> _handleLogin(BuildContext context, AuthProvider authProvider) async {
    if (!authProvider.loginFormKey.currentState!.validate()) return;
    final success = await authProvider.login(
      authProvider.loginEmailController.text,
      authProvider.loginPasswordController.text,
    );

    if (success && context.mounted) {
      authProvider.resetLoginForm();
      Navigator.of(context).pushReplacementNamed(AppRoutes.home);
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.xl,
            ),
            child: Form(
              key: authProvider.loginFormKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const AuthHeader(
                    title: 'Welcome Back',
                    subtitle: 'Sign in to access your smart home security ecosystem',
                    icon: Icons.shield_outlined,
                  ),
                  const SizedBox(height: AppSpacing.xl),

                  // Error notification banner if authentication error exists
                  if (authProvider.errorMessage != null) ...[
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(AppSpacing.md),
                      margin: const EdgeInsets.only(bottom: AppSpacing.lg),
                      decoration: BoxDecoration(
                        color: AppColors.champagneSoft,
                        borderRadius: BorderRadius.circular(AppSpacing.radiusSm),
                        border: Border.all(
                          color: AppColors.error.withValues(alpha: 0.3),
                          width: 1.0,
                        ),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.error_outline_rounded,
                            color: AppColors.error,
                            size: 20,
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: Text(
                              authProvider.errorMessage!,
                              style: AppTextStyles.bodyMedium.copyWith(
                                color: AppColors.error,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],

                  // Email input field
                  AuthTextField(
                    controller: authProvider.loginEmailController,
                    label: 'Email Address',
                    hint: 'user@example.com',
                    prefixIcon: Icons.mail_outline_rounded,
                    keyboardType: TextInputType.emailAddress,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter your email address.';
                      }
                      if (!value.trim().contains('@')) {
                        return 'Please enter a valid email address.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: AppSpacing.md),

                  // Password input field with ValueListenableBuilder toggle
                  ValueListenableBuilder<bool>(
                    valueListenable: authProvider.loginPasswordObscured,
                    builder: (context, isObscured, _) {
                      return AuthTextField(
                        controller: authProvider.loginPasswordController,
                        label: 'Password',
                        hint: '••••••••',
                        prefixIcon: Icons.lock_outline_rounded,
                        obscureText: isObscured,
                        suffixIcon: IconButton(
                          icon: Icon(
                            isObscured
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                            color: AppColors.textSecondary,
                            size: 20,
                          ),
                          onPressed: () {
                            authProvider.toggleLoginPasswordVisibility();
                          },
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Please enter your password.';
                          }
                          return null;
                        },
                      );
                    },
                  ),
                  const SizedBox(height: AppSpacing.xl),

                  // Primary Sign In Button
                  AuthButton(
                    text: 'Sign In',
                    isLoading: authProvider.isLoading,
                    onPressed: () => _handleLogin(context, authProvider),
                  ),
                  const SizedBox(height: AppSpacing.lg),

                  // Navigation to Register Screen
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        "Don't have an account? ",
                        style: AppTextStyles.bodyMedium,
                      ),
                      GestureDetector(
                        onTap: () {
                          authProvider.clearError();
                          Navigator.of(context).pushNamed(AppRoutes.register);
                        },
                        child: Text(
                          'Create Account',
                          style: AppTextStyles.label.copyWith(
                            color: AppColors.black,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
