import 'package:flutter/material.dart';
import 'package:mobile/app/theme/app_colors.dart';
import 'package:mobile/models/member_model.dart';
import 'package:mobile/features/members/widgets/member_avatar.dart';

class MemberListItem extends StatelessWidget {
  final MemberModel member;
  final String? homeName;
  final VoidCallback onTap;

  const MemberListItem({super.key, required this.member, required this.onTap, this.homeName});

  @override
  Widget build(BuildContext context) {
    final hasFace = member.faceCount > 0;
    final secondary = [if (member.relation?.trim().isNotEmpty == true) member.relation!.trim(), if (homeName?.trim().isNotEmpty == true) homeName!.trim()].join(' · ');
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.border))),
        child: Row(children: [
          MemberAvatar(name: member.name, size: 42, hasRegisteredFace: hasFace),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(member.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.textPrimary, fontSize: 12, fontWeight: FontWeight.w700)),
            const SizedBox(height: 3),
            Text(secondary.isEmpty ? 'Home member' : secondary, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.textSecondary, fontSize: 10)),
          ])),
          const SizedBox(width: 6),
          Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.circle, size: 5, color: hasFace ? AppColors.success : AppColors.textMuted),
            const SizedBox(width: 4),
            Text(hasFace ? 'Face ready' : 'Face not set', style: TextStyle(color: hasFace ? AppColors.forest : AppColors.textSecondary, fontSize: 9, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(width: 5),
          const Icon(Icons.chevron_right_rounded, color: AppColors.textMuted, size: 18),
        ]),
      ),
    );
  }
}
