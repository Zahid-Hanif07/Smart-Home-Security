import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/providers/auth_provider.dart';
import 'package:mobile/providers/home_provider.dart';

class EditHomeScreen extends StatefulWidget {
  const EditHomeScreen({super.key});

  @override
  State<EditHomeScreen> createState() => _EditHomeScreenState();
}

class _EditHomeScreenState extends State<EditHomeScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _addressController = TextEditingController();
  String? _loadedHomeId;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final home = context.read<HomeProvider>().currentHome;
    if (home != null && home.id != _loadedHomeId) {
      _loadedHomeId = home.id;
      _nameController.text = home.name;
      _addressController.text = home.address ?? '';
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final homes = context.read<HomeProvider>();
    final home = homes.currentHome;
    if (home == null) return;
    final updated = await homes.updateHome(
      context.read<AuthProvider>().token,
      home.id,
      _nameController.text,
      _addressController.text,
    );
    if (updated != null && mounted) Navigator.of(context).pop();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final homes = context.watch<HomeProvider>();
    if (homes.currentHome == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Edit home')),
        body: const Center(child: Text('Select a home before editing.')),
      );
    }
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('Edit home')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              children: [
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: 'Home name'),
                  validator: (value) => value == null || value.trim().isEmpty
                      ? 'Enter a home name.'
                      : null,
                ),
                TextFormField(
                  controller: _addressController,
                  decoration: const InputDecoration(labelText: 'Address (optional)'),
                ),
                if (homes.errorMessage != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(homes.errorMessage!, style: const TextStyle(color: AppColors.error)),
                  ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: homes.isLoading ? null : _save,
                    child: homes.isLoading
                        ? const CircularProgressIndicator()
                        : const Text('Save changes'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
