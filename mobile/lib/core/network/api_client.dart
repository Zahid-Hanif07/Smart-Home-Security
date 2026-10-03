import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/core/network/api_exception.dart';

class ApiClient {
  final http.Client _client;
  final Duration timeout;

  ApiClient({
    http.Client? client,
    this.timeout = const Duration(seconds: 5),
  }) : _client = client ?? http.Client();

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
      final uri = Uri.parse('${ApiConfig.baseUrl}$endpoint').replace(
        queryParameters: queryParameters,
      );
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

  Future<dynamic> delete(
    String endpoint, {
    String? token,
  }) async {
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

  // ---------------------------------------------------------------------------
  // MEMBER API CONVENIENCE METHODS
  // ---------------------------------------------------------------------------
  Future<List<dynamic>> getMembers(String homeId, String? token) async {
    final res = await get('/api/homes/$homeId/members', token: token);
    if (res is List) return res;
    return [];
  }

  Future<dynamic> createMember(String homeId, Map<String, dynamic> body, String? token) async {
    return await post('/api/homes/$homeId/members', body: body, token: token);
  }

  Future<dynamic> updateMember(String memberId, Map<String, dynamic> body, String? token) async {
    return await put('/api/members/$memberId', body: body, token: token);
  }

  Future<dynamic> deleteMember(String memberId, String? token) async {
    return await delete('/api/members/$memberId', token: token);
  }

  // ---------------------------------------------------------------------------
  // FACE API CONVENIENCE METHODS
  // ---------------------------------------------------------------------------
  Future<List<dynamic>> getFaces(String memberId, String? token) async {
    final res = await get('/api/members/$memberId/faces', token: token);
    if (res is List) return res;
    return [];
  }

  Future<dynamic> registerFace(String memberId, Map<String, dynamic> body, String? token) async {
    return await post('/api/members/$memberId/register-face', body: body, token: token);
  }

  Future<dynamic> deleteFace(String faceId, String? token) async {
    return await delete('/api/faces/$faceId', token: token);
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
