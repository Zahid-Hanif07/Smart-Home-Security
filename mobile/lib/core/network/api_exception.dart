class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic details;

  ApiException({
    required this.message,
    this.statusCode,
    this.details,
  });

  factory ApiException.fromStatusCode(int code, [dynamic body]) {
    String detailMsg = '';
    if (body is Map && body.containsKey('detail')) {
      detailMsg = ': ${body['detail']}';
    }

    switch (code) {
      case 400:
        return ApiException(
          message: 'Bad Request$detailMsg',
          statusCode: 400,
          details: body,
        );
      case 401:
        return ApiException(
          message: 'Unauthorized access$detailMsg',
          statusCode: 401,
          details: body,
        );
      case 403:
        return ApiException(
          message: "You don't have permission to perform this action.$detailMsg",
          statusCode: 403,
          details: body,
        );
      case 404:
        return ApiException(
          message: 'Resource not found$detailMsg',
          statusCode: 404,
          details: body,
        );
      case 422:
        return ApiException(
          message: 'Validation error$detailMsg',
          statusCode: 422,
          details: body,
        );
      case 500:
      case 502:
      case 503:
        return ApiException(
          message: 'Server error. Please try again later.',
          statusCode: code,
          details: body,
        );
      default:
        return ApiException(
          message: 'Unexpected error ($code)$detailMsg',
          statusCode: code,
          details: body,
        );
    }
  }

  factory ApiException.connectionError() {
    return ApiException(
      message: 'Unable to connect to server. Please check your connection and verify FastAPI is running.',
      statusCode: null,
    );
  }

  factory ApiException.timeoutError() {
    return ApiException(
      message: 'Request timed out. Please try again.',
      statusCode: null,
    );
  }

  @override
  String toString() => message;
}
