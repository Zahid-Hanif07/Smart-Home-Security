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
import 'package:mobile/features/home/presentation/edit_home_screen.dart';
import 'package:mobile/features/profile/presentation/profile_screen.dart';
import 'package:mobile/features/profile/presentation/settings_screen.dart';
import 'package:mobile/features/home/presentation/alerts_screen.dart';
import 'package:mobile/features/voice/presentation/voice_assistant_screen.dart';

class AppRoutes {
  static final RouteObserver<ModalRoute<dynamic>> observer =
      RouteObserver<ModalRoute<dynamic>>();

  static const String splash = '/splash';
  static const String onboarding = '/onboarding';
  static const String login = '/login';
  static const String register = '/register';
  static const String home = '/home';
  static const String homes = '/homes';
  static const String addHome = '/add-home';
  static const String editHome = '/edit-home';
  static const String members = '/members';
  static const String addMember = '/add-member';
  static const String memberDetail = '/member-detail';
  static const String registerFace = '/register-face';
  static const String profile = '/profile';
  static const String settings = '/settings';
  static const String alerts = '/alerts';
  static const String voiceAssistant = '/voice-assistant';

  static Map<String, WidgetBuilder> get routes {
    return {
      splash: (context) => const SplashScreen(),
      onboarding: (context) => const OnboardingScreen(),
      login: (context) => const LoginScreen(),
      register: (context) => const RegisterScreen(),
      home: (context) => const HomeScreen(),
      homes: (context) => const HomeManagementScreen(),
      addHome: (context) => const AddHomeScreen(),
      editHome: (context) => const EditHomeScreen(),
      members: (context) => const MembersScreen(),
      addMember: (context) => const AddMemberScreen(),
      memberDetail: (context) => const MemberDetailScreen(),
      registerFace: (context) => const RegisterFaceScreen(),
      profile: (context) => const ProfileScreen(),
      settings: (context) => const SettingsScreen(),
      alerts: (context) => const AlertsScreen(),
      voiceAssistant: (context) => const VoiceAssistantScreen(),
    };
  }
}
