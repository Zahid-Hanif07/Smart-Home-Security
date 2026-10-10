import 'package:flutter/material.dart';
import 'package:mobile/core/storage/local_storage.dart';

/// Manages PageView index, controllers, and onboarding completion state.
/// Ensures UI widgets remain pure StatelessWidgets.
class OnboardingProvider extends ChangeNotifier {
  late PageController _pageController;
  int _currentPage = 0;
  bool _isNavigating = false;

  OnboardingProvider() {
    _pageController = PageController();
  }

  PageController get pageController => _pageController;
  int get currentPage => _currentPage;
  bool get isLastPage => _currentPage == 2;
  bool get isNavigating => _isNavigating;

  /// Update page index when user swipes or page completes transition
  void onPageChanged(int index) {
    if (_currentPage != index) {
      _currentPage = index;
      notifyListeners();
    }
  }

  /// Go to the next page smoothly
  void nextPage() {
    if (_currentPage < 2 && _pageController.hasClients) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  /// Go to the previous page if available
  void previousPage() {
    if (_currentPage > 0 && _pageController.hasClients) {
      _pageController.previousPage(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  /// Mark onboarding as completed and navigate to the target route
  Future<void> completeOnboarding(BuildContext context, {required String targetRoute}) async {
    if (_isNavigating) return;
    _isNavigating = true;
    notifyListeners();

    await LocalStorage.setOnboardingCompleted(true);

    if (context.mounted) {
      Navigator.of(context).pushReplacementNamed(targetRoute);
    }
    _isNavigating = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }
}
