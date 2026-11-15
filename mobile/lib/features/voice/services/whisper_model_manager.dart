import 'dart:io';

import 'package:flutter/services.dart';

enum WhisperModelStatus { notDownloaded, ready, error }

class WhisperModelPaths {
  const WhisperModelPaths({
    required this.encoder,
    required this.decoder,
    required this.tokens,
  });

  final String encoder;
  final String decoder;
  final String tokens;
}

class WhisperModelManager {
  static const _channel = MethodChannel('otto.voice/model');

  Future<WhisperModelPaths?> resolve() async {
    try {
      final directory = await _channel.invokeMethod<String>('modelDirectory');
      if (directory == null || directory.isEmpty) return null;
      return WhisperModelPaths(
        encoder: '$directory/tiny-encoder.onnx',
        decoder: '$directory/tiny-decoder.int8.onnx',
        tokens: '$directory/tiny-tokens.txt',
      );
    } on PlatformException {
      return null;
    }
  }

  Future<WhisperModelStatus> status() async {
    final paths = await resolve();
    if (paths == null) return WhisperModelStatus.error;
    final files = [paths.encoder, paths.decoder, paths.tokens]
        .map(File.new);
    return (await Future.wait(files.map((file) => file.exists()))).every(
      (exists) => exists,
    )
        ? WhisperModelStatus.ready
        : WhisperModelStatus.notDownloaded;
  }
}
