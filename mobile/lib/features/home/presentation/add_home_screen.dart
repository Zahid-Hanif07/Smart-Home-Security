import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/app/theme/app_spacing.dart';
import 'package:mobile/app/theme/app_text_styles.dart';
import 'package:mobile/core/widgets/app_button.dart';
import 'package:mobile/core/widgets/app_text_field.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

class AddHomeScreen extends StatelessWidget {
  const AddHomeScreen({super.key});

  Future<void> _handleSubmit(BuildContext context, AuthProvider authProvider, HomeProvider homeProvider) async {
    if (!homeProvider.addHomeFormKey.currentState!.validate()) return;
    final newHome = await homeProvider.createHome(
      authProvider.token,
      homeProvider.addHomeNameController.text.trim(),
      homeProvider.addHomeAddressController.text.trim(),
    );

    if (newHome != null && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${newHome.name} created successfully!'),
          backgroundColor: AppColors.success,
        ),
      );
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final homeProvider = Provider.of<HomeProvider>(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: const IconThemeData(color: AppColors.black),
        title: const Text(
          'Add New Home',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Form(
            key: homeProvider.addHomeFormKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Property Information',
                  style: AppTextStyles.heading2,
                ),
                const SizedBox(height: AppSpacing.xs),
                const Text(
                  'Register a new home property to pair security hardware and configure authorized family members.',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: AppSpacing.xl),

                if (homeProvider.errorMessage != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(AppSpacing.md),
                    margin: const EdgeInsets.only(bottom: AppSpacing.lg),
                    decoration: BoxDecoration(
                      color: AppColors.champagneSoft,
                      borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
                      border: Border.all(
                        color: AppColors.error.withValues(alpha: 0.3),
                      ),
                    ),
                    child: Text(
                      homeProvider.errorMessage!,
                      style: const TextStyle(
                        color: AppColors.error,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],

                // Home Name Field
                AppTextField(
                  controller: homeProvider.addHomeNameController,
                  label: 'Home / Property Name',
                  hint: 'e.g. Main Residence, Beach House',
                  prefixIcon: Icons.home_rounded,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter a name for your home.';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: AppSpacing.md),

                // Address Field (Optional)
                AppTextField(
                  controller: homeProvider.addHomeAddressController,
                  label: 'Property Address (Optional)',
                  hint: 'e.g. 124 Ocean Drive, Suite 4B',
                  prefixIcon: Icons.location_on_outlined,
                ),
                const SizedBox(height: AppSpacing.xl),

                AppButton(
                  text: 'Save & Select Home',
                  isLoading: homeProvider.isLoading,
                  onPressed: () => _handleSubmit(context, Provider.of<AuthProvider>(context, listen: false), homeProvider),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
