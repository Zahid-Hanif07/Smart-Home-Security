import 'package:flutter/material.dart';
import 'package:mobile/features/splash/presentation/splash_screen.dart';
import 'package:mobile/features/onboarding/presentation/onboarding_screen.dart';
import 'package:mobile/features/auth/presentation/login_screen.dart';
import 'package:mobile/features/auth/presentation/register_screen.dart';
import 'package:mobile/features/home/presentation/home_screen.dart';
import 'package:mobile/features/members/presentation/members_screen.dart';
import 'package:mobile/features/members/presentation/add_member_screen.dart';
import 'package:mobile/features/members/presentation/member_detail_screen.dart';
import 'package:mobile/features/members/presentation/register_face_screen.dart';

import 'package:mobile/features/home/presentation/home_management_screen.dart';
import 'package:mobile/features/home/presentation/add_home_screen.dart';

class AppRoutes {
  static const String splash = '/splash';
  static const String onboarding = '/onboarding';
  static const String login = '/login';
  static const String register = '/register';
  static const String home = '/home';
  static const String homes = '/homes';
  static const String addHome = '/add-home';
  static const String members = '/members';
  static const String addMember = '/add-member';
  static const String memberDetail = '/member-detail';
  static const String registerFace = '/register-face';

  static Map<String, WidgetBuilder> get routes {
    return {
      splash: (context) => const SplashScreen(),
      onboarding: (context) => const OnboardingScreen(),
      login: (context) => const LoginScreen(),
      register: (context) => const RegisterScreen(),
      home: (context) => const HomeScreen(),
      homes: (context) => const HomeManagementScreen(),
      addHome: (context) => const AddHomeScreen(),
      members: (context) => const MembersScreen(),
      addMember: (context) => const AddMemberScreen(),
      memberDetail: (context) => const MemberDetailScreen(),
      registerFace: (context) => const RegisterFaceScreen(),
    };
  }
}
