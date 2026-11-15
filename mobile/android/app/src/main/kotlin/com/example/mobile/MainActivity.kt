package com.example.mobile

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile

class MainActivity : FlutterActivity() {
    private val channelName = "otto.voice/audio"
    private val modelChannelName = "otto.voice/model"
    private val permissionRequestCode = 4010
    private val sampleRate = 16_000
    private var audioRecord: AudioRecord? = null
    private var recordingThread: Thread? = null
    private var activeFile: File? = null
    private var activeOutput: FileOutputStream? = null
    private var lastFile: File? = null
    private var pcmBytes = 0
    private var pendingStartResult: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result -> handleCall(call, result) }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, modelChannelName)
            .setMethodCallHandler { call, result ->
                if (call.method == "modelDirectory") {
                    result.success(File(filesDir, "models/whisper-tiny").absolutePath)
                } else {
                    result.notImplemented()
                }
            }
    }

    private fun handleCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "isAvailable" -> result.success(
                packageManager.hasSystemFeature(PackageManager.FEATURE_MICROPHONE)
            )
            "startRecording" -> startRecording(result)
            "stopRecording" -> stopRecording(result)
            "cancelRecording" -> {
                cancelRecording()
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    private fun startRecording(result: MethodChannel.Result) {
        if (audioRecord != null) {
            result.error("already_recording", "Recording is already active.", null)
            return
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            pendingStartResult = result
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                permissionRequestCode,
            )
            return
        }
        try {
            lastFile?.delete()
            lastFile = null
            val minBuffer = AudioRecord.getMinBufferSize(
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            if (minBuffer <= 0) throw IllegalStateException("Audio input unavailable")
            val bufferSize = maxOf(minBuffer, sampleRate / 2)
            val file = File(cacheDir, "otto_voice_" + System.currentTimeMillis() + ".wav")
            val output = FileOutputStream(file)
            output.write(ByteArray(44))
            val record = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sampleRate,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize,
            )
            if (record.state != AudioRecord.STATE_INITIALIZED) {
                output.close()
                file.delete()
                record.release()
                throw IllegalStateException("Audio input could not be initialized")
            }
            pcmBytes = 0
            activeFile = file
            activeOutput = output
            audioRecord = record
            record.startRecording()
            recordingThread = Thread {
                val buffer = ByteArray(bufferSize)
                while (audioRecord === record) {
                    val read = record.read(buffer, 0, buffer.size)
                    if (read > 0) {
                        synchronized(this) {
                            activeOutput?.write(buffer, 0, read)
                            pcmBytes += read
                        }
                    }
                }
            }.also { it.start() }
            result.success(true)
        } catch (_: Exception) {
            cancelRecording()
            result.error("recording_failed", "Recording could not be started.", null)
        }
    }

    private fun stopRecording(result: MethodChannel.Result) {
        val record = audioRecord
        val file = activeFile
        if (record == null || file == null) {
            result.error("not_recording", "No recording is active.", null)
            return
        }
        try {
            audioRecord = null
            record.stop()
            recordingThread?.join(1000)
            recordingThread = null
            record.release()
            activeOutput?.close()
            activeOutput = null
            writeWavHeader(file, pcmBytes)
            activeFile = null
            lastFile = file
            result.success(file.absolutePath)
        } catch (_: Exception) {
            cancelRecording()
            result.error("recording_failed", "Recording could not be stopped safely.", null)
        }
    }

    private fun cancelRecording() {
        val record = audioRecord
        audioRecord = null
        try {
            record?.stop()
        } catch (_: Exception) {
        }
        recordingThread?.join(500)
        recordingThread = null
        record?.release()
        activeOutput?.close()
        activeOutput = null
        activeFile?.delete()
        activeFile = null
        lastFile?.delete()
        lastFile = null
    }

    private fun writeWavHeader(file: File, dataLength: Int) {
        RandomAccessFile(file, "rw").use { wav ->
            wav.seek(0)
            wav.writeBytes("RIFF")
            writeIntLE(wav, 36 + dataLength)
            wav.writeBytes("WAVEfmt ")
            writeIntLE(wav, 16)
            writeShortLE(wav, 1)
            writeShortLE(wav, 1)
            writeIntLE(wav, sampleRate)
            writeIntLE(wav, sampleRate * 2)
            writeShortLE(wav, 2)
            writeShortLE(wav, 16)
            wav.writeBytes("data")
            writeIntLE(wav, dataLength)
        }
    }

    private fun writeIntLE(file: RandomAccessFile, value: Int) {
        file.write(value and 0xff)
        file.write(value shr 8 and 0xff)
        file.write(value shr 16 and 0xff)
        file.write(value shr 24 and 0xff)
    }

    private fun writeShortLE(file: RandomAccessFile, value: Int) {
        file.write(value and 0xff)
        file.write(value shr 8 and 0xff)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != permissionRequestCode) return
        val result = pendingStartResult ?: return
        pendingStartResult = null
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            startRecording(result)
        } else {
            result.error("permission_denied", "Microphone permission is required.", null)
        }
    }

    override fun onDestroy() {
        pendingStartResult?.error("cancelled", "Recording was cancelled.", null)
        pendingStartResult = null
        cancelRecording()
        super.onDestroy()
    }
}
