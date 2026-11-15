import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/models/voice_command_model.dart';
import 'package:mobile/models/room_model.dart';

class ApiClient {
  final http.Client _client;
  final Duration timeout;

  ApiClient({http.Client? client, this.timeout = const Duration(seconds: 15)})
    : _client = client ?? http.Client();

  Map<String, String> _buildHeaders(String? token) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<dynamic> get(
    String endpoint, {
    String? token,
    Map<String, String>? queryParameters,
  }) async {
    try {
      final uri = Uri.parse(
        '${ApiConfig.baseUrl}$endpoint',
      ).replace(queryParameters: queryParameters);
      final response = await _client
          .get(uri, headers: _buildHeaders(token))
          .timeout(timeout);

      return _processResponse(response);
    } on TimeoutException {
      throw ApiException.timeoutError();
    } on http.ClientException {
      throw ApiException.connectionError();
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException.connectionError();
    }
  }

  Future<dynamic> post(
    String endpoint, {
    Map<String, dynamic>? body,
    String? token,
  }) async {
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}$endpoint');
      final response = await _client
          .post(
            uri,
            headers: _buildHeaders(token),
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(timeout);

      return _processResponse(response);
    } on TimeoutException {
      throw ApiException.timeoutError();
    } on http.ClientException {
      throw ApiException.connectionError();
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException.connectionError();
    }
  }

  Future<dynamic> put(
    String endpoint, {
    Map<String, dynamic>? body,
    String? token,
  }) async {
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}$endpoint');
      final response = await _client
          .put(
            uri,
            headers: _buildHeaders(token),
            body: body != null ? jsonEncode(body) : null,
          )
          .timeout(timeout);

      return _processResponse(response);
    } on TimeoutException {
      throw ApiException.timeoutError();
    } on http.ClientException {
      throw ApiException.connectionError();
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException.connectionError();
    }
  }

  Future<dynamic> delete(String endpoint, {String? token}) async {
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}$endpoint');
      final response = await _client
          .delete(uri, headers: _buildHeaders(token))
          .timeout(timeout);

      return _processResponse(response);
    } on TimeoutException {
      throw ApiException.timeoutError();
    } on http.ClientException {
      throw ApiException.connectionError();
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException.connectionError();
    }
  }

  Future<bool> checkHealth() async {
    try {
      final data = await get(ApiConfig.healthEndpoint);
      if (data is Map && data['status'] == 'ok') {
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<dynamic> getVideoStatus(String homeId, String? token) async {
    if (homeId.isEmpty) {
      throw ApiException(message: 'home_id cannot be empty.');
    }
    return get(
      ApiConfig.videoStatusEndpoint,
      token: token,
      queryParameters: {'home_id': homeId},
    );
  }

  Future<dynamic> getFaceOcclusionStatus(String homeId, String? token) async {
    final cleanHomeId = homeId.trim();
    if (cleanHomeId.isEmpty) {
      throw ApiException(message: 'home_id cannot be empty.');
    }
    return get(
      ApiConfig.faceOcclusionStatusEndpoint,
      token: token,
      queryParameters: {'home_id': cleanHomeId},
    );
  }

  Future<VoiceCommandSubmission> createVoiceCommand(
    String homeId,
    String clientCommandId,
    String command,
    String targetType,
    String? roomId,
    String? token,
  ) async {
    final cleanHomeId = homeId.trim();
    if (cleanHomeId.isEmpty || clientCommandId.trim().isEmpty) {
      throw ApiException(message: 'A home and command ID are required.');
    }
    final body = <String, dynamic>{
      'client_command_id': clientCommandId,
      'command': command,
      'target_type': targetType,
      ...?roomId == null ? null : {'room_id': roomId},
    };
    final response = await post(
      '/api/homes/$cleanHomeId/commands',
      body: body,
      token: token,
    );
    if (response is! Map || response['command'] is! Map) {
      throw ApiException(
        message: 'The server returned an invalid command response.',
      );
    }
    return VoiceCommandSubmission.fromJson(Map<String, dynamic>.from(response));
  }

  Future<VoiceCommandModel> getVoiceCommand(
    String homeId,
    String commandId,
    String? token,
  ) async {
    final response = await get(
      '/api/homes/${homeId.trim()}/commands/${commandId.trim()}',
      token: token,
    );
    if (response is! Map) {
      throw ApiException(
        message: 'The server returned an invalid command response.',
      );
    }
    return VoiceCommandModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<List<RoomModel>> getHomeRooms(String homeId, String? token) async {
    final cleanHomeId = homeId.trim();
    if (cleanHomeId.isEmpty) {
      throw ApiException(message: 'home_id cannot be empty.');
    }
    final response = await get('/api/homes/$cleanHomeId/rooms', token: token);
    if (response is! Map || response['rooms'] is! List) {
      throw ApiException(
        message: 'The server returned an invalid rooms response.',
      );
    }
    return (response['rooms'] as List)
        .map(
          (room) => RoomModel.fromJson(Map<String, dynamic>.from(room as Map)),
        )
        .toList();
  }

  // ---------------------------------------------------------------------------
  // MEMBER API CONVENIENCE METHODS
  // ---------------------------------------------------------------------------
  Future<List<dynamic>> getMembers(String homeId, String? token) async {
    final cleanHomeId = homeId.trim();
    if (cleanHomeId.isEmpty) {
      throw ApiException(
        message:
            'home_id cannot be empty. Please select or create a home first.',
      );
    }
    final res = await get('/api/homes/$cleanHomeId/members', token: token);
    if (res is List) return res;
    return [];
  }

  Future<dynamic> createMember(
    String homeId,
    Map<String, dynamic> body,
    String? token,
  ) async {
    final cleanHomeId = homeId.trim();
    if (cleanHomeId.isEmpty) {
      throw ApiException(
        message:
            'home_id cannot be empty. Please select or create a home first.',
      );
    }
    return await post(
      '/api/homes/$cleanHomeId/members',
      body: body,
      token: token,
    );
  }

  Future<dynamic> updateMember(
    String memberId,
    Map<String, dynamic> body,
    String? token,
  ) async {
    final cleanMemberId = memberId.trim();
    if (cleanMemberId.isEmpty) {
      throw ApiException(message: 'member_id cannot be empty.');
    }
    return await put('/api/members/$cleanMemberId', body: body, token: token);
  }

  Future<dynamic> deleteMember(String memberId, String? token) async {
    final cleanMemberId = memberId.trim();
    if (cleanMemberId.isEmpty) {
      throw ApiException(message: 'member_id cannot be empty.');
    }
    return await delete('/api/members/$cleanMemberId', token: token);
  }

  // ---------------------------------------------------------------------------
  // FACE API CONVENIENCE METHODS
  // ---------------------------------------------------------------------------
  Future<List<dynamic>> getFaces(String memberId, String? token) async {
    final cleanMemberId = memberId.trim();
    if (cleanMemberId.isEmpty) {
      throw ApiException(message: 'member_id cannot be empty.');
    }
    final res = await get('/api/members/$cleanMemberId/faces', token: token);
    if (res is List) return res;
    return [];
  }

  Future<dynamic> registerFace(
    String memberId,
    Map<String, dynamic> body,
    String? token,
  ) async {
    final cleanMemberId = memberId.trim();
    if (cleanMemberId.isEmpty) {
      throw ApiException(message: 'member_id cannot be empty.');
    }
    return await post(
      '/api/members/$cleanMemberId/register-face',
      body: body,
      token: token,
    );
  }

  Future<dynamic> deleteFace(String faceId, String? token) async {
    final cleanFaceId = faceId.trim();
    if (cleanFaceId.isEmpty) {
      throw ApiException(message: 'face_id cannot be empty.');
    }
    return await delete('/api/faces/$cleanFaceId', token: token);
  }

  Future<dynamic> clearMemberFaces(String memberId, String? token) async {
    final cleanMemberId = memberId.trim();
    if (cleanMemberId.isEmpty) {
      throw ApiException(message: 'member_id cannot be empty.');
    }
    return await delete('/api/members/$cleanMemberId/faces', token: token);
  }

  dynamic _processResponse(http.Response response) {
    final statusCode = response.statusCode;
    dynamic bodyData;

    if (response.body.isNotEmpty) {
      try {
        bodyData = jsonDecode(response.body);
      } catch (_) {
        bodyData = response.body;
      }
    }

    if (statusCode >= 200 && statusCode < 300) {
      return bodyData;
    } else {
      throw ApiException.fromStatusCode(statusCode, bodyData);
    }
  }
}
