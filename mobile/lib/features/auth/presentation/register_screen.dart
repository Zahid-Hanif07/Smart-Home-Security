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

/// RegisterScreen - StatelessWidget Mobile Identity
class RegisterScreen extends StatelessWidget {
  const RegisterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final formKey = GlobalKey<FormState>();
    final nameController = TextEditingController();
    final emailController = TextEditingController();
    final passwordController = TextEditingController();
    final confirmPasswordController = TextEditingController();
    final obscurePasswordNotifier = ValueNotifier<bool>(true);

    Future<void> handleRegister() async {
      if (!formKey.currentState!.validate()) return;

      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final success = await authProvider.register(
        nameController.text,
        emailController.text,
        passwordController.text,
      );

      if (!context.mounted) return;
      if (success) {
        Navigator.of(context).pushNamedAndRemoveUntil(
          AppRoutes.home,
          (route) => false,
        );
      }
    }

    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: AppColors.black),
          onPressed: () {
            authProvider.clearError();
            Navigator.of(context).pop();
          },
        ),
        elevation: 0,
        backgroundColor: AppColors.background,
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.md,
            ),
            child: Form(
              key: formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const AuthHeader(
                    title: 'Create Account',
                    subtitle: 'Register your profile to manage smart home security',
                    icon: Icons.person_add_outlined,
                  ),
                  const SizedBox(height: AppSpacing.xl),

                  // Error notification banner if registration error exists
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

                  // Full Name input field
                  AuthTextField(
                    controller: nameController,
                    label: 'Full Name',
                    hint: 'Alex Morgan',
                    prefixIcon: Icons.person_outline_rounded,
                    textCapitalization: TextCapitalization.words,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter your full name.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: AppSpacing.md),

                  // Email input field
                  AuthTextField(
                    controller: emailController,
                    label: 'Email Address',
                    hint: 'user@example.com',
                    prefixIcon: Icons.mail_outline_rounded,
                    keyboardType: TextInputType.emailAddress,
                    validator: (value) {
                      if (value == null || value.trim().isEmpty) {
                        return 'Please enter an email address.';
                      }
                      if (!value.contains('@')) {
                        return 'Please enter a valid email address.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: AppSpacing.md),

                  // Password input field
                  ValueListenableBuilder<bool>(
                    valueListenable: obscurePasswordNotifier,
                    builder: (context, isObscured, _) {
                      return Column(
                        children: [
                          AuthTextField(
                            controller: passwordController,
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
                                obscurePasswordNotifier.value = !isObscured;
                              },
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please enter a password.';
                              }
                              if (value.length < 6) {
                                return 'Password must be at least 6 characters.';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: AppSpacing.md),
                          AuthTextField(
                            controller: confirmPasswordController,
                            label: 'Confirm Password',
                            hint: '••••••••',
                            prefixIcon: Icons.lock_reset_rounded,
                            obscureText: isObscured,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please confirm your password.';
                              }
                              if (value != passwordController.text) {
                                return 'Passwords do not match.';
                              }
                              return null;
                            },
                          ),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: AppSpacing.xl),

                  // Register Button
                  AuthButton(
                    text: 'Register Account',
                    isLoading: authProvider.isLoading,
                    onPressed: handleRegister,
                  ),
                  const SizedBox(height: AppSpacing.lg),

                  // Navigation back to Login Screen
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        'Already have an account? ',
                        style: AppTextStyles.bodyMedium,
                      ),
                      GestureDetector(
                        onTap: () {
                          authProvider.clearError();
                          Navigator.of(context).pop();
                        },
                        child: Text(
                          'Sign In',
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
