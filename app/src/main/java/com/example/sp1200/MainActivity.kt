package com.example.sp1200

import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.midi.MidiDevice
import android.media.midi.MidiDeviceInfo
import android.media.midi.MidiManager
import android.media.midi.MidiReceiver
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.provider.MediaStore
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.json.JSONArray
import org.json.JSONObject

private fun <T> List<List<T>>.set2(a: Int, b: Int, value: T): List<List<T>> {
    return this.toMutableList().also { outer ->
        outer[a] = outer[a].toMutableList().also { inner ->
            inner[b] = value
        }
    }
}

class MainActivity : ComponentActivity() {

    companion object {
        init {
            System.loadLibrary("native-lib")
        }
    }

    private external fun nativeSetup()
    private external fun nativeStart()
    private external fun nativeStop()
    private external fun nativeRelease()
    private external fun nativeTriggerPad(padIndex: Int)
    private external fun nativePadRelease(padIndex: Int)
    private external fun nativeSetGateMode(enabled: Boolean)
    private external fun nativeSetPitch(semitones: Float)
    private external fun nativeSetCrunch(enabled: Boolean)
    private external fun nativeSetBank(bank: Int)
    private external fun nativeSetMute(padIndex: Int, enabled: Boolean)
    private external fun nativeSetSolo(padIndex: Int, enabled: Boolean)
    private external fun nativeLoadSample(padIndex: Int, fd: Int): Boolean
    private external fun nativePreviewFromFd(fd: Int): Boolean
    private external fun nativeSeqSetPlaying(playing: Boolean)
    private external fun nativeSeqSetBpm(bpm: Float)
    private external fun nativeSeqSetSwing(swing: Float)
    private external fun nativeSeqSetMask(padIndex: Int, mask: Int)
    private external fun nativeSetRoll(padIndex: Int, step: Int, value: Int, len: Int)
    private external fun nativeSetLoopPoints(padIndex: Int, startFrac: Float, endFrac: Float)
    private external fun nativeSetLoopOn(padIndex: Int, enabled: Boolean)
    private external fun nativeTrimToLoop(padIndex: Int): Boolean
    private external fun nativeGetPeaks(padIndex: Int, buckets: Int): FloatArray
    private external fun nativeSetPadParams(
        padIndex: Int,
        pitch: Float,
        attack: Float,
        decay: Float,
        sustain: Float,
        release: Float
    )
    private external fun nativeSetPadVol(padIndex: Int, vol: Float)
    private external fun nativeSetPadPan(padIndex: Int, pan: Float)
    private external fun nativeSetMasterVol(vol: Float)
    private external fun nativeSetMasterPan(pan: Float)
    private external fun nativeSetMidiMode(mode: Int)
    private external fun nativeMidiTick()
    private external fun nativeMidiStart()
    private external fun nativeMidiStop()
    private external fun nativeGetMidiTicks(): Long
    private external fun nativeSetDataDir(dir: String)
    private external fun nativeGetCurrentStep(): Int
    private external fun nativeGetPadHits(padIndex: Int): Long
    private external fun nativeStartRecording(padIndex: Int): Boolean
    private external fun nativeStopRecording(): Boolean
    private external fun nativeStartCapture()
    private external fun nativeStopCapture(path: String): Boolean

    private lateinit var midiManager: MidiManager
    private var midiDevice: MidiDevice? = null
    private var sendFn: ((ByteArray) -> Unit)? = null
    private var closePortsFn: (() -> Unit)? = null

    @Volatile
    private var clockRunning = false
    private var clockThread: Thread? = null
    private var lastTicks = 0L

    private val pollHandler = Handler(Looper.getMainLooper())
    private var prevHits = MutableList(16) { 0L }

    private var pendingPad by mutableStateOf(-1)
    private var bank by mutableStateOf(0)
    private var loadedBanks by mutableStateOf(List(4) { setOf<Int>() })
    private var gateMode by mutableStateOf(false)
    private var pitch by mutableStateOf(0f)
    private var crunch by mutableStateOf(true)
    private var view by mutableStateOf(0)
    private var playing by mutableStateOf(false)
    private var bpm by mutableStateOf(90f)
    private var swing by mutableStateOf(0f)
    private var patternBanks by mutableStateOf(List(4) { List(16) { 0 } })
    private var rollBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })
    private var rollLenBanks by mutableStateOf(List(4) { List(16) { List(16) { 0 } } })
    private var noteLen by mutableStateOf(1)
    private var mutes by mutableStateOf(List(16) { false })
    private var solos by mutableStateOf(List(16) { false })
    private var midiMode by mutableStateOf(0)
    private var midiDeviceName by mutableStateOf("none")
    private var recording by mutableStateOf(false)
    private var playhead by mutableStateOf(0)
    private var pollTick by mutableStateOf(0)
    private var hitTimes by mutableStateOf(List(16) { 0L })
    private var libFiles by mutableStateOf(listOf<String>())
    private var mixAssign by mutableStateOf(List(5) { it })
    private var volBanks by mutableStateOf(List(16) { 100f })
    private var panBanks by mutableStateOf(List(16) { 50f })
    private var masterVol by mutableStateOf(100f)
    private var masterPan by mutableStateOf(50f)
    private var exportBars by mutableStateOf(2)
    private var exporting by mutableStateOf(false)
    private var exportWasPlaying = false

    private var selectedPad by mutableStateOf(0)
    private var peaks by mutableStateOf(FloatArray(0))
    private var loopStartBanks by mutableStateOf(List(4) { List(16) { 0f } })
    private var loopEndBanks by mutableStateOf(List(4) { List(16) { 100f } })
    private var loopOnBanks by mutableStateOf(List(4) { List(16) { false } })

    private var pitchBanks by mutableStateOf(List(4) { List(16) { 0f } })
    private var attackBanks by mutableStateOf(List(4) { List(16) { 0f } })
    private var decayBanks by mutableStateOf(List(4) { List(16) { 0f } })
    private var sustainBanks by mutableStateOf(List(4) { List(16) { 100f } })
    private var releaseBanks by mutableStateOf(List(4) { List(16) { 50f } })

    private fun libraryDir(): File {
        val dir = File(filesDir, "library")
        dir.mkdirs()
        return dir
    }

    private fun refreshLib() {
        libFiles = libraryDir().listFiles()
            ?.filter { it.isFile && it.name.lowercase().endsWith(".wav") }
            ?.map { it.name }
            ?.sorted()
            ?: emptyList()
    }

    private fun isRiffWav(f: File): Boolean {
        return try {
            val head = ByteArray(12)
            f.inputStream().use { ins ->
                var off = 0
                while (off < 12) {
                    val r = ins.read(head, off, 12 - off)
                    if (r < 0) break
                    off += r
                }
            }
            String(head, 0, 4) == "RIFF" && String(head, 8, 4) == "WAVE"
        } catch (_: Exception) {
            false
        }
    }

    private fun writeWavKt(target: File, mono: FloatArray, rate: Int) {
        val n = mono.size
        val bb = ByteBuffer.allocate(44 + n * 2).order(ByteOrder.LITTLE_ENDIAN)
        bb.put("RIFF".toByteArray())
        bb.putInt(36 + n * 2)
        bb.put("WAVE".toByteArray())
        bb.put("fmt ".toByteArray())
        bb.putInt(16)
        bb.putShort(1)
        bb.putShort(1)
        bb.putInt(rate)
        bb.putInt(rate * 2)
        bb.putShort(2)
        bb.putShort(16)
        bb.put("data".toByteArray())
        bb.putInt(n * 2)
        for (v in mono) {
            val c = v.coerceIn(-1f, 1f)
            bb.putShort((c * 32767f).toInt().toShort())
        }
        target.writeBytes(bb.array())
    }

    private fun convertWavFile(file: File): Boolean {
        try {
            val bytes = file.readBytes()
            if (bytes.size < 44) return false
            if (String(bytes, 0, 4) != "RIFF" || String(bytes, 8, 4) != "WAVE") return false

            val bb = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            var pos = 12
            var format = 0
            var channels = 0
            var bits = 0
            var rate = 44100
            var dataOff = -1
            var dataSize = 0

            while (pos + 8 <= bytes.size) {
                val id = String(bytes, pos, 4)
                val size = bb.getInt(pos + 4)
                val body = pos + 8

                if (id == "fmt " && size >= 16) {
                    format = bb.getShort(body).toInt() and 0xFFFF
                    channels = bb.getShort(body + 2).toInt() and 0xFFFF
                    rate = bb.getInt(body + 4)
                    bits = bb.getShort(body + 14).toInt() and 0xFFFF
                } else if (id == "data") {
                    dataOff = body
                    dataSize = size
                }

                pos = body + size + (size and 1)
            }

            if (dataOff < 0 || channels <= 0 || rate <= 0) return false
            if (format == 1 && bits == 16) return true

            val bytesPer = bits / 8
            if (bytesPer <= 0) return false
            val frameBytes = channels * bytesPer
            var frames = dataSize / frameBytes
            val maxFrames = (bytes.size - dataOff) / frameBytes
            if (frames > maxFrames) frames = maxFrames
            if (frames <= 0) return false

            val mono = FloatArray(frames)
            for (i in 0 until frames) {
                var acc = 0f
                for (c in 0 until channels) {
                    val o = dataOff + i * frameBytes + c * bytesPer
                    acc += when {
                        format == 1 && bits == 8 ->
                            ((bytes[o].toInt() and 0xFF) - 128) / 128f
                        format == 1 && bits == 16 ->
                            bb.getShort(o).toInt() / 32768f
                        format == 1 && bits == 24 -> {
                            val b0 = bytes[o].toInt() and 0xFF
                            val b1 = bytes[o + 1].toInt() and 0xFF
                            val b2 = bytes[o + 2].toInt()
                            ((b2 shl 16) or (b1 shl 8) or b0) / 8388608f
                        }
                        format == 1 && bits == 32 ->
                            bb.getInt(o) / 2147483648f
                        format == 3 && bits == 32 ->
                            bb.getFloat(o)
                        else -> return false
                    }
                }
                mono[i] = acc / channels
            }

            writeWavKt(file, mono, rate)
            return true
        } catch (_: Exception) {
            return false
        }
    }

    private fun decodeAudioToWav(uri: Uri, target: File): Boolean {
        var decoder: MediaCodec? = null
        var extractor: MediaExtractor? = null
        try {
            extractor = MediaExtractor()
            extractor.setDataSource(this, uri, null)

            var track = -1
            var format: MediaFormat? = null
            for (i in 0 until extractor.trackCount) {
                val f = extractor.getTrackFormat(i)
                val mime = f.getString(MediaFormat.KEY_MIME) ?: continue
                if (mime.startsWith("audio/")) {
                    track = i
                    format = f
                    break
                }
            }
            if (track < 0 || format == null) return false

            extractor.selectTrack(track)

            val mime = format.getString(MediaFormat.KEY_MIME) ?: return false
            decoder = MediaCodec.createDecoderByType(mime)
            decoder.configure(format, null, null, 0)
            decoder.start()

            val pcm = ArrayList<Short>()
            val info = MediaCodec.BufferInfo()
            var inputDone = false
            var outputDone = false
            var gotFormat = false
            var sampleRate = 44100
            var channels = 1
            val timeout = 10000L

            while (!outputDone) {
                if (!inputDone) {
                    val inIdx = decoder.dequeueInputBuffer(timeout)
                    if (inIdx >= 0) {
                        val buf = decoder.getInputBuffer(inIdx)
                        if (buf == null) {
                            decoder.queueInputBuffer(inIdx, 0, 0, 0, 0)
                        } else {
                            buf.clear()
                            val n = extractor.readSampleData(buf, 0)
                            if (n < 0) {
                                decoder.queueInputBuffer(
                                    inIdx, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM
                                )
                                inputDone = true
                            } else {
                                decoder.queueInputBuffer(inIdx, 0, n, extractor.sampleTime, 0)
                                extractor.advance()
                            }
                        }
                    }
                }

                val outIdx = decoder.dequeueOutputBuffer(info, timeout)
                if (outIdx >= 0) {
                    if (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) {
                        decoder.releaseOutputBuffer(outIdx, false)
                    } else {
                        if (!gotFormat) {
                            val of = decoder.outputFormat
                            if (of.containsKey(MediaFormat.KEY_SAMPLE_RATE)) {
                                sampleRate = of.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                            }
                            if (of.containsKey(MediaFormat.KEY_CHANNEL_COUNT)) {
                                channels = of.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                            }
                            gotFormat = true
                        }

                        val buf = decoder.getOutputBuffer(outIdx)
                        if (buf != null && info.size > 0) {
                            val arr = ByteArray(info.size)
                            buf.get(arr)
                            for (j in 0 until info.size / 2) {
                                val lo = arr[j * 2].toInt() and 0xFF
                                val hi = arr[j * 2 + 1].toInt()
                                pcm.add(((hi shl 8) or lo).toShort())
                            }
                        }
                        decoder.releaseOutputBuffer(outIdx, false)

                        if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) {
                            outputDone = true
                        }
                    }
                }
            }

            decoder.stop()
            decoder.release()
            decoder = null
            extractor.release()
            extractor = null

            if (pcm.isEmpty() || channels <= 0) return false

            val frames = pcm.size / channels
            if (frames <= 0) return false
            val mono = FloatArray(frames)
            for (i in 0 until frames) {
                var acc = 0f
                for (c in 0 until channels) {
                    acc += pcm[i * channels + c] / 32768f
                }
                mono[i] = acc / channels
            }

            writeWavKt(target, mono, sampleRate)
            return true
        } catch (_: Exception) {
            return false
        } finally {
            try {
                decoder?.release()
            } catch (_: Exception) {
            }
            try {
                extractor?.release()
            } catch (_: Exception) {
            }
        }
    }

    private fun previewFile(name: String) {
        val f = File(libraryDir(), name)
        if (!f.exists()) return
        try {
            ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY).use { pfd ->
                if (!nativePreviewFromFd(pfd.fd)) {
                    Toast.makeText(this, "Preview failed: $name", Toast.LENGTH_SHORT).show()
                }
            }
        } catch (_: Exception) {
        }
    }

    private fun assignFile(pad: Int, name: String) {
        val f = File(libraryDir(), name)
        if (!f.exists()) return
        try {
            ParcelFileDescriptor.open(f, ParcelFileDescriptor.MODE_READ_ONLY).use { pfd ->
                if (nativeLoadSample(pad, pfd.fd)) {
                    loadedBanks = loadedBanks.toMutableList().also { it[bank] = it[bank] + pad }
                    if (pad == selectedPad) {
                        peaks = nativeGetPeaks(pad, 200)
                    }
                    Toast.makeText(this, "PAD ${pad + 1}: $name", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this, "Load failed: $name", Toast.LENGTH_SHORT).show()
                }
            }
        } catch (_: Exception) {
        }
    }

    private fun auditionPitch(pad: Int, semi: Int) {
        val p = pitchBanks[bank][pad]
        val a = attackBanks[bank][pad]
        val d = decayBanks[bank][pad]
        val s = sustainBanks[bank][pad]
        val r = releaseBanks[bank][pad]

        nativeSetPadParams(pad, semi.toFloat(), a, d, s, r)
        nativeTriggerPad(pad)

        pollHandler.postDelayed({
            nativeSetPadParams(pad, p, a, d, s, r)
        }, 100)
    }

    private fun startExport() {
        if (exporting) return
        exporting = true
        exportWasPlaying = playing

        nativeStartCapture()
        playing = true
        nativeSeqSetPlaying(true)

        val secPerStep = (60.0 / bpm.toDouble()) / 4.0
        val totalMs = (secPerStep * 16 * exportBars * 1000).toLong()

        Toast.makeText(this, "Exporting $exportBars bars...", Toast.LENGTH_SHORT).show()

        pollHandler.postDelayed({
            if (!exportWasPlaying) {
                playing = false
                nativeSeqSetPlaying(false)
            }

            pollHandler.postDelayed({
                val dir = File(filesDir, "exports")
                dir.mkdirs()
                val f = File(dir, "sp1200_beat.wav")
                val ok = nativeStopCapture(f.absolutePath)
                exporting = false

                if (ok) {
                    Toast.makeText(this, "Exported!", Toast.LENGTH_SHORT).show()
                    publishAndShare(f)
                } else {
                    Toast.makeText(this, "Export failed", Toast.LENGTH_SHORT).show()
                }
            }, 1000)
        }, totalMs)
    }

    private fun publishAndShare(internalFile: File) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(
                        MediaStore.MediaColumns.DISPLAY_NAME,
                        "sp1200_beat_${System.currentTimeMillis()}.wav"
                    )
                    put(MediaStore.MediaColumns.MIME_TYPE, "audio/wav")
                    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                }

                val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                if (uri != null) {
                    contentResolver.openOutputStream(uri)?.use { outs ->
                        internalFile.inputStream().use { it.copyTo(outs) }
                    }

                    val share = Intent(Intent.ACTION_SEND).apply {
                        type = "audio/wav"
                        putExtra(Intent.EXTRA_STREAM, uri)
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    startActivity(Intent.createChooser(share, "Share beat"))
                }
            } else {
                Toast.makeText(this, "Saved: ${internalFile.absolutePath}", Toast.LENGTH_LONG).show()
            }
        } catch (_: Exception) {
            Toast.makeText(this, "Saved: ${internalFile.absolutePath}", Toast.LENGTH_LONG).show()
        }
    }

    private fun pushPadParams(pad: Int) {
        nativeSetPadParams(
            pad,
            pitchBanks[bank][pad],
            attackBanks[bank][pad] / 1000f,
            decayBanks[bank][pad] / 1000f,
            sustainBanks[bank][pad] / 100f,
            releaseBanks[bank][pad] / 1000f
        )
    }

    private val midiReceiver = object : MidiReceiver() {
        override fun onSend(msg: ByteArray, offset: Int, count: Int, timestamp: Long) {
            for (i in offset until offset + count) {
                when (msg[i].toInt() and 0xFF) {
                    0xF8 -> nativeMidiTick()
                    0xFA -> nativeMidiStart()
                    0xFC -> nativeMidiStop()
                }
            }
        }
    }

    private val recPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                startRec()
            }
        }

    private fun startRec() {
        if (nativeStartRecording(selectedPad)) {
            recording = true
            Toast.makeText(this, "Recording... press REC to stop", Toast.LENGTH_SHORT).show()
        }
    }

    private fun onRecToggle() {
        if (recording) {
            recording = false
            val ok = nativeStopRecording()
            if (ok) {
                loadedBanks = loadedBanks.toMutableList().also { it[bank] = it[bank] + selectedPad }
                peaks = nativeGetPeaks(selectedPad, 200)
                refreshLib()
                Toast.makeText(this, "Recorded to PAD ${selectedPad + 1}", Toast.LENGTH_SHORT).show()
            }
        } else {
            if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
            ) {
                startRec()
            } else {
                recPermission.launch(android.Manifest.permission.RECORD_AUDIO)
            }
        }
    }

    private val importLauncher =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            if (uri == null) return@registerForActivityResult
            try {
                val rawName = uri.lastPathSegment ?: "import.wav"
                var safe = rawName.replace(Regex("[^a-zA-Z0-9._-]"), "_")
                if (!safe.lowercase().endsWith(".wav")) safe += ".wav"

                val dir = libraryDir()
                var target = File(dir, safe)
                var counter = 1
                while (target.exists()) {
                    target = File(dir, "imp${counter}_$safe")
                    counter++
                }

                contentResolver.openInputStream(uri)?.use { ins ->
                    target.outputStream().use { outs ->
                        ins.copyTo(outs)
                    }
                }

                val ok = if (isRiffWav(target)) {
                    convertWavFile(target)
                } else {
                    decodeAudioToWav(uri, target)
                }

                if (!ok) {
                    target.delete()
                    Toast.makeText(this, "Unsupported audio format", Toast.LENGTH_SHORT).show()
                    return@registerForActivityResult
                }

                refreshLib()
                Toast.makeText(this, "Imported: ${target.name}", Toast.LENGTH_SHORT).show()
            } catch (_: Exception) {
            }
        }

    private fun saveState() {
        try {
            val root = JSONObject()
            root.put("bank", bank)
            root.put("bpm", bpm)
            root.put("swing", swing)
            root.put("crunch", crunch)
            root.put("gate", gateMode)
            root.put("pitch", pitch)
            root.put("mutes", JSONArray(mutes))
            root.put("solos", JSONArray(solos))
            root.put("vol", JSONArray(volBanks))
            root.put("pan", JSONArray(panBanks))
            root.put("mvol", masterVol)
            root.put("mpan", masterPan)

            val banksArr = JSONArray()
            for (b in 0 until 4) {
                val bo = JSONObject()
                bo.put("patterns", JSONArray(patternBanks[b]))

                val rollArr = JSONArray()
                val rollLenArr = JSONArray()
                for (p in 0 until 16) {
                    rollArr.put(JSONArray(rollBanks[b][p]))
                    rollLenArr.put(JSONArray(rollLenBanks[b][p]))
                }
                bo.put("roll", rollArr)
                bo.put("rolllen", rollLenArr)

                val loopsArr = JSONArray()
                for (p in 0 until 16) {
                    val lo = JSONObject()
                    lo.put("s", loopStartBanks[b][p])
                    lo.put("e", loopEndBanks[b][p])
                    lo.put("on", loopOnBanks[b][p])
                    loopsArr.put(lo)
                }
                bo.put("loops", loopsArr)

                val paramsArr = JSONArray()
                for (p in 0 until 16) {
                    val po = JSONObject()
                    po.put("p", pitchBanks[b][p])
                    po.put("a", attackBanks[b][p])
                    po.put("d", decayBanks[b][p])
                    po.put("s", sustainBanks[b][p])
                    po.put("r", releaseBanks[b][p])
                    paramsArr.put(po)
                }
                bo.put("params", paramsArr)

                banksArr.put(bo)
            }
            root.put("banks", banksArr)

            File(filesDir, "state.json").writeText(root.toString())
        } catch (_: Exception) {
        }
    }

    private fun loadState() {
        try {
            val f = File(filesDir, "state.json")
            if (!f.exists()) return

            val root = JSONObject(f.readText())
            bank = root.optInt("bank", 0)
            bpm = root.optDouble("bpm", 90.0).toFloat()
            swing = root.optDouble("swing", 0.0).toFloat()
            crunch = root.optBoolean("crunch", true)
            gateMode = root.optBoolean("gate", false)
            pitch = root.optDouble("pitch", 0.0).toFloat()

            root.optJSONArray("mutes")?.let { m ->
                mutes = (0 until 16).map { m.optBoolean(it, false) }
            }
            root.optJSONArray("solos")?.let { s ->
                solos = (0 until 16).map { s.optBoolean(it, false) }
            }
            root.optJSONArray("vol")?.let { va ->
                volBanks = (0 until 16).map { va.optDouble(it, 100.0).toFloat() }
            }
            root.optJSONArray("pan")?.let { va ->
                panBanks = (0 until 16).map { va.optDouble(it, 50.0).toFloat() }
            }
            masterVol = root.optDouble("mvol", 100.0).toFloat()
            masterPan = root.optDouble("mpan", 50.0).toFloat()

            val banksArr = root.optJSONArray("banks") ?: return

            val newPatterns = patternBanks.toMutableList()
            val newRolls = rollBanks.toMutableList()
            val newRollLens = rollLenBanks.toMutableList()
            val newLS = loopStartBanks.toMutableList()
            val newLE = loopEndBanks.toMutableList()
            val newLO = loopOnBanks.toMutableList()
            val newP = pitchBanks.toMutableList()
            val newA = attackBanks.toMutableList()
            val newD = decayBanks.toMutableList()
            val newS = sustainBanks.toMutableList()
            val newR = releaseBanks.toMutableList()

            for (b in 0 until minOf(4, banksArr.length())) {
                val bo = banksArr.optJSONObject(b) ?: continue

                bo.optJSONArray("patterns")?.let { pat ->
                    newPatterns[b] = (0 until 16).map { pat.optInt(it, 0) }
                }

                bo.optJSONArray("roll")?.let { ra ->
                    val rows = rollBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ra.length())) {
                        val st = ra.optJSONArray(p) ?: continue
                        rows[p] = (0 until 16).map { st.optInt(it, 0) }
                    }
                    newRolls[b] = rows
                }

                bo.optJSONArray("rolllen")?.let { ra ->
                    val rows = rollLenBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ra.length())) {
                        val st = ra.optJSONArray(p) ?: continue
                        rows[p] = (0 until 16).map { st.optInt(it, 0) }
                    }
                    newRollLens[b] = rows
                }

                bo.optJSONArray("loops")?.let { la ->
                    for (p in 0 until minOf(16, la.length())) {
                        val lo = la.optJSONObject(p) ?: continue
                        newLS[b] = newLS[b].toMutableList().also { it[p] = lo.optDouble("s", 0.0).toFloat() }
                        newLE[b] = newLE[b].toMutableList().also { it[p] = lo.optDouble("e", 100.0).toFloat() }
                        newLO[b] = newLO[b].toMutableList().also { it[p] = lo.optBoolean("on", false) }
                    }
                }

                bo.optJSONArray("params")?.let { pa ->
                    for (p in 0 until minOf(16, pa.length())) {
                        val po = pa.optJSONObject(p) ?: continue
                        newP[b] = newP[b].toMutableList().also { it[p] = po.optDouble("p", 0.0).toFloat() }
                        newA[b] = newA[b].toMutableList().also { it[p] = po.optDouble("a", 0.0).toFloat() }
                        newD[b] = newD[b].toMutableList().also { it[p] = po.optDouble("d", 0.0).toFloat() }
                        newS[b] = newS[b].toMutableList().also { it[p] = po.optDouble("s", 100.0).toFloat() }
                        newR[b] = newR[b].toMutableList().also { it[p] = po.optDouble("r", 50.0).toFloat() }
                    }
                }
            }

            patternBanks = newPatterns
            rollBanks = newRolls
            rollLenBanks = newRollLens
            loopStartBanks = newLS
            loopEndBanks = newLE
            loopOnBanks = newLO
            pitchBanks = newP
            attackBanks = newA
            decayBanks = newD
            sustainBanks = newS
            releaseBanks = newR
        } catch (_: Exception) {
        }
    }

    private fun pushAllToNative() {
        nativeSetGateMode(gateMode)
        nativeSetPitch(pitch)
        nativeSetCrunch(crunch)
        nativeSeqSetBpm(bpm)
        nativeSeqSetSwing(swing / 100f)

        for (p in 0 until 16) {
            nativeSetMute(p, mutes[p])
            nativeSetSolo(p, solos[p])
            nativeSetPadVol(p, volBanks[p] / 100f)
            nativeSetPadPan(p, (panBanks[p] - 50f) / 50f)
        }
        nativeSetMasterVol(masterVol / 100f)
        nativeSetMasterPan((masterPan - 50f) / 50f)

        for (b in 0 until 4) {
            nativeSetBank(b)
            for (p in 0 until 16) {
                nativeSeqSetMask(p, patternBanks[b][p])
                for (st in 0 until 16) {
                    nativeSetRoll(p, st, rollBanks[b][p][st], rollLenBanks[b][p][st])
                }
                nativeSetLoopPoints(p, loopStartBanks[b][p] / 100f, loopEndBanks[b][p] / 100f)
                nativeSetLoopOn(p, loopOnBanks[b][p])
                nativeSetPadParams(
                    p,
                    pitchBanks[b][p],
                    attackBanks[b][p] / 1000f,
                    decayBanks[b][p] / 1000f,
                    sustainBanks[b][p] / 100f,
                    releaseBanks[b][p] / 1000f
                )
            }
        }

        nativeSetBank(bank)
    }

    private fun restoreSamples() {
        val dir = File(filesDir, "samples")
        if (!dir.exists()) return

        for (b in 0 until 4) {
            nativeSetBank(b)
            for (p in 0 until 16) {
                val f = File(dir, "b${b}_p$p.wav")
                if (f.exists()) {
                    try {
                        ParcelFileDescriptor.open(
                            f,
                            ParcelFileDescriptor.MODE_READ_ONLY
                        ).use { pfd ->
                            if (nativeLoadSample(p, pfd.fd)) {
                                loadedBanks = loadedBanks.toMutableList().also { it[b] = it[b] + p }
                            }
                        }
                    } catch (_: Exception) {
                    }
                }
            }
        }

        nativeSetBank(bank)
    }

    private fun teardownMidi() {
        clockRunning = false
        clockThread = null
        try {
            closePortsFn?.invoke()
        } catch (_: Exception) {
        }
        closePortsFn = null
        sendFn = null
        try {
            midiDevice?.close()
        } catch (_: Exception) {
        }
        midiDevice = null
        midiDeviceName = "none"
    }

    private fun openMaster() {
        val info = midiManager.devices.firstOrNull { it.inputPortCount > 0 }
        if (info == null) {
            Toast.makeText(this, "No MIDI output device", Toast.LENGTH_SHORT).show()
            return
        }

        midiManager.openDevice(info, { device ->
            midiDevice = device
            val port = device.openInputPort(0)

            if (port != null) {
                sendFn = { data ->
                    try {
                        port.send(data, 0, data.size, 0)
                    } catch (_: Exception) {
                    }
                }
                closePortsFn = {
                    try {
                        port.close()
                    } catch (_: Exception) {
                    }
                }
            }

            midiDeviceName = info.properties.getString(MidiDeviceInfo.PROPERTY_NAME) ?: "midi"
            startClockThread()
        }, null)
    }

    private fun openSlave() {
        val info = midiManager.devices.firstOrNull { it.outputPortCount > 0 }
        if (info == null) {
            Toast.makeText(this, "No MIDI input device", Toast.LENGTH_SHORT).show()
            return
        }

        midiManager.openDevice(info, { device ->
            midiDevice = device
            val port = device.openOutputPort(0)

            if (port != null) {
                try {
                    val m = port.javaClass.getMethod("setReceiver", MidiReceiver::class.java)
                    m.invoke(port, midiReceiver)
                } catch (_: Exception) {
                }
                closePortsFn = {
                    try {
                        port.close()
                    } catch (_: Exception) {
                    }
                }
            }

            midiDeviceName = info.properties.getString(MidiDeviceInfo.PROPERTY_NAME) ?: "midi"
        }, null)
    }

    private fun startClockThread() {
        clockRunning = true
        lastTicks = 0L

        clockThread = Thread {
            while (clockRunning) {
                val cur = nativeGetMidiTicks()
                val delta = cur - lastTicks

                if (delta > 0) {
                    val arr = ByteArray(delta.toInt()) { 0xF8.toByte() }
                    sendFn?.invoke(arr)
                    lastTicks = cur
                }

                try {
                    Thread.sleep(1)
                } catch (_: InterruptedException) {
                    return@Thread
                }
            }
        }.also { it.start() }
    }

    private fun applyMidiMode(mode: Int) {
        teardownMidi()
        nativeSetMidiMode(mode)

        if (mode == 1) {
            openMaster()
        } else if (mode == 2) {
            openSlave()
        }
    }

    private fun sendMidiByte(b: Int) {
        sendFn?.invoke(byteArrayOf(b.toByte()))
    }

    private val pickSample =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            val pad = pendingPad
            pendingPad = -1

            if (uri != null && pad >= 0) {
                contentResolver.openFileDescriptor(uri, "r")?.use { pfd ->
                    val ok = nativeLoadSample(pad, pfd.fd)
                    if (ok) {
                        loadedBanks = loadedBanks.toMutableList().also { it[bank] = it[bank] + pad }
                        loopStartBanks = loopStartBanks.set2(bank, pad, 0f)
                        loopEndBanks = loopEndBanks.set2(bank, pad, 100f)
                        if (pad == selectedPad) {
                            peaks = nativeGetPeaks(pad, 200)
                        }
                        Toast.makeText(this, "PAD ${pad + 1}: sample loaded", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this, "Need PCM 16-bit WAV", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        nativeSetup()

        val samplesDir = File(filesDir, "samples")
        samplesDir.mkdirs()
        nativeSetDataDir(samplesDir.absolutePath)

        loadState()
        pushAllToNative()
        restoreSamples()
        refreshLib()

        midiManager = getSystemService(MIDI_SERVICE) as MidiManager

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF0C1416)
                ) {
                    Sp1200App(
                        onPadDown = { nativeTriggerPad(it) },
                        onPadUp = { nativePadRelease(it) },
                        onPadLongPress = { pad ->
                            pendingPad = pad
                            pickSample.launch(arrayOf("audio/*"))
                        },
                        loadedPads = loadedBanks[bank],
                        gateMode = gateMode,
                        onGateModeChange = { enabled ->
                            gateMode = enabled
                            nativeSetGateMode(enabled)
                        },
                        pitch = pitch,
                        onPitchChange = { value ->
                            pitch = value
                            nativeSetPitch(value)
                        },
                        crunch = crunch,
                        onCrunchChange = { enabled ->
                            crunch = enabled
                            nativeSetCrunch(enabled)
                        },
                        bank = bank,
                        onBankChange = { b ->
                            bank = b
                            nativeSetBank(b)
                            peaks = nativeGetPeaks(selectedPad, 200)
                        },
                        view = view,
                        onViewChange = { v ->
                            view = v
                            if (v == 4) refreshLib()
                        },
                        playing = playing,
                        onPlayToggle = {
                            playing = !playing
                            nativeSeqSetPlaying(playing)

                            if (midiMode == 1) {
                                sendMidiByte(if (playing) 0xFA else 0xFC)
                            }
                        },
                        bpm = bpm,
                        onBpmChange = { value ->
                            bpm = value
                            nativeSeqSetBpm(value)
                        },
                        swing = swing,
                        onSwingChange = { value ->
                            swing = value
                            nativeSeqSetSwing(value / 100f)
                        },
                        pattern = patternBanks[bank],
                        onToggleStep = { pad, step ->
                            val newMask = patternBanks[bank][pad] xor (1 shl step)
                            patternBanks = patternBanks.set2(bank, pad, newMask)
                            nativeSeqSetMask(pad, newMask)
                        },
                        mutes = mutes,
                        onMuteToggle = { pad ->
                            val v = !mutes[pad]
                            mutes = mutes.toMutableList().also { it[pad] = v }
                            nativeSetMute(pad, v)
                        },
                        solos = solos,
                        onSoloToggle = { pad ->
                            val v = !solos[pad]
                            solos = solos.toMutableList().also { it[pad] = v }
                            nativeSetSolo(pad, v)
                        },
                        midiMode = midiMode,
                        midiDeviceName = midiDeviceName,
                        onMidiModeChange = {
                            val next = (midiMode + 1) % 3
                            midiMode = next
                            applyMidiMode(next)
                        },
                        roll = rollBanks[bank],
                        rollLens = rollLenBanks[bank],
                        noteLen = noteLen,
                        onNoteLenCycle = {
                            noteLen = when (noteLen) {
                                1 -> 2
                                2 -> 4
                                else -> 1
                            }
                        },
                        onToggleRollCell = { pad, step, enc ->
                            val row = rollBanks[bank][pad]
                            val rowLen = rollLenBanks[bank][pad]

                            var coverStart = -1
                            if (row[step] == enc) {
                                coverStart = step
                            } else {
                                for (s0 in 0 until step) {
                                    if (row[s0] == enc && step < s0 + rowLen[s0]) {
                                        coverStart = s0
                                        break
                                    }
                                }
                            }

                            if (coverStart >= 0) {
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[coverStart] = 0 }
                                )
                                rollLenBanks = rollLenBanks.set2(
                                    bank, pad,
                                    rollLenBanks[bank][pad].toMutableList().also { it[coverStart] = 0 }
                                )
                                nativeSetRoll(pad, coverStart, 0, 1)
                            } else {
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[step] = enc }
                                )
                                rollLenBanks = rollLenBanks.set2(
                                    bank, pad,
                                    rollLenBanks[bank][pad].toMutableList().also { it[step] = noteLen }
                                )
                                nativeSetRoll(pad, step, enc, noteLen)
                            }
                        },
                        onAudition = { pad, semi -> auditionPitch(pad, semi) },
                        playhead = playhead,
                        flashes = hitTimes.map { System.currentTimeMillis() - it < 150 },
                        recording = recording,
                        onRecToggle = { onRecToggle() },
                        libFiles = libFiles,
                        onImport = { importLauncher.launch(arrayOf("audio/*")) },
                        onPreview = { name -> previewFile(name) },
                        onAssign = { pad, name -> assignFile(pad, name) },
                        mixAssign = mixAssign,
                        onMixAssignCycle = { i ->
                            mixAssign = mixAssign.toMutableList().also { it[i] = (it[i] + 1) % 16 }
                        },
                        volOf = { p -> volBanks[p] },
                        panOf = { p -> panBanks[p] },
                        onVol = { p, value ->
                            volBanks = volBanks.toMutableList().also { it[p] = value }
                            nativeSetPadVol(p, value / 100f)
                        },
                        onPan = { p, value ->
                            panBanks = panBanks.toMutableList().also { it[p] = value }
                            nativeSetPadPan(p, (value - 50f) / 50f)
                        },
                        masterVol = masterVol,
                        onMasterVol = { value ->
                            masterVol = value
                            nativeSetMasterVol(value / 100f)
                        },
                        masterPan = masterPan,
                        onMasterPan = { value ->
                            masterPan = value
                            nativeSetMasterPan((value - 50f) / 50f)
                        },
                        exportBars = exportBars,
                        onExportBarsCycle = {
                            exportBars = when (exportBars) {
                                1 -> 2
                                2 -> 4
                                else -> 1
                            }
                        },
                        exporting = exporting,
                        onExport = { startExport() },
                        selectedPad = selectedPad,
                        onSelectPad = { pad ->
                            selectedPad = pad
                            peaks = nativeGetPeaks(pad, 200)
                        },
                        peaks = peaks,
                        loopStart = loopStartBanks[bank][selectedPad],
                        loopEnd = loopEndBanks[bank][selectedPad],
                        onLoopStart = { value ->
                            val end = loopEndBanks[bank][selectedPad]
                            val clamped = if (value > end - 1f) end - 1f else value
                            loopStartBanks = loopStartBanks.set2(bank, selectedPad, clamped)
                            nativeSetLoopPoints(selectedPad, clamped / 100f, end / 100f)
                        },
                        onLoopEnd = { value ->
                            val start = loopStartBanks[bank][selectedPad]
                            val clamped = if (value < start + 1f) start + 1f else value
                            loopEndBanks = loopEndBanks.set2(bank, selectedPad, clamped)
                            nativeSetLoopPoints(selectedPad, start / 100f, clamped / 100f)
                        },
                        loopOn = loopOnBanks[bank][selectedPad],
                        onLoopToggle = {
                            val newOn = !loopOnBanks[bank][selectedPad]
                            loopOnBanks = loopOnBanks.set2(bank, selectedPad, newOn)
                            nativeSetLoopOn(selectedPad, newOn)
                        },
                        onTrim = {
                            val ok = nativeTrimToLoop(selectedPad)
                            if (ok) {
                                loopStartBanks = loopStartBanks.set2(bank, selectedPad, 0f)
                                loopEndBanks = loopEndBanks.set2(bank, selectedPad, 100f)
                                nativeSetLoopPoints(selectedPad, 0f, 1f)
                                peaks = nativeGetPeaks(selectedPad, 200)
                                Toast.makeText(this, "Trimmed", Toast.LENGTH_SHORT).show()
                            }
                        },
                        onPlayDown = { nativeTriggerPad(selectedPad) },
                        onPlayUp = { nativePadRelease(selectedPad) },
                        padPitch = pitchBanks[bank][selectedPad],
                        onPadPitch = { value ->
                            pitchBanks = pitchBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padAttack = attackBanks[bank][selectedPad],
                        onPadAttack = { value ->
                            attackBanks = attackBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padDecay = decayBanks[bank][selectedPad],
                        onPadDecay = { value ->
                            decayBanks = decayBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padSustain = sustainBanks[bank][selectedPad],
                        onPadSustain = { value ->
                            sustainBanks = sustainBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padReleaseMs = releaseBanks[bank][selectedPad],
                        onPadReleaseMs = { value ->
                            releaseBanks = releaseBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padVol = volBanks[selectedPad],
                        onPadVol = { value ->
                            volBanks = volBanks.toMutableList().also { it[selectedPad] = value }
                            nativeSetPadVol(selectedPad, value / 100f)
                        },
                        padPan = panBanks[selectedPad],
                        onPadPan = { value ->
                            panBanks = panBanks.toMutableList().also { it[selectedPad] = value }
                            nativeSetPadPan(selectedPad, (value - 50f) / 50f)
                        }
                    )
                }
            }
        }
    }

    override fun onStart() {
        super.onStart()
        nativeStart()

        pollHandler.post(object : Runnable {
            override fun run() {
                playhead = nativeGetCurrentStep()

                val now = System.currentTimeMillis()
                val newTimes = hitTimes.toMutableList()
                for (i in 0 until 16) {
                    val h = nativeGetPadHits(i)
                    if (h != prevHits[i]) {
                        newTimes[i] = now
                        prevHits[i] = h
                    }
                }
                hitTimes = newTimes
                pollTick++

                pollHandler.postDelayed(this, 50)
            }
        })
    }

    override fun onStop() {
        super.onStop()
        pollHandler.removeCallbacksAndMessages(null)
        saveState()
        nativeStop()
    }

    override fun onDestroy() {
        teardownMidi()
        nativeRelease()
        super.onDestroy()
    }
}

fun padColor(index: Int): Color = when (index) {
    0 -> Color(0xFF2DD4BF)
    1 -> Color(0xFF4CC3E0)
    2 -> Color(0xFF7FA8F0)
    3 -> Color(0xFFA78BFA)
    4 -> Color(0xFFE07FA0)
    5 -> Color(0xFFF0A45C)
    6 -> Color(0xFFB8E05C)
    7 -> Color(0xFF5EEAD4)
    8 -> Color(0xFF38BDF8)
    9 -> Color(0xFF818CF8)
    10 -> Color(0xFFC084FC)
    11 -> Color(0xFFF472B6)
    12 -> Color(0xFFFBBF24)
    13 -> Color(0xFFA3E635)
    14 -> Color(0xFF34D399)
    else -> Color(0xFF22D3EE)
}

@Composable
fun RowScope.SmallButton(
    label: String,
    active: Boolean,
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        modifier = Modifier
            .weight(1f)
            .height(32.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (active) Color(0xFF2DD4BF) else Color(0xFF152528)
        ),
        contentPadding = PaddingValues(horizontal = 2.dp, vertical = 2.dp)
    ) {
        Text(
            text = label,
            color = if (active) Color(0xFF06201D) else Color(0xFFBFE6E2),
            fontSize = 10.sp,
            maxLines = 1
        )
    }
}

@Composable
fun Sp1200App(
    onPadDown: (Int) -> Unit,
    onPadUp: (Int) -> Unit,
    onPadLongPress: (Int) -> Unit,
    loadedPads: Set<Int>,
    gateMode: Boolean,
    onGateModeChange: (Boolean) -> Unit,
    pitch: Float,
    onPitchChange: (Float) -> Unit,
    crunch: Boolean,
    onCrunchChange: (Boolean) -> Unit,
    bank: Int,
    onBankChange: (Int) -> Unit,
    view: Int,
    onViewChange: (Int) -> Unit,
    playing: Boolean,
    onPlayToggle: () -> Unit,
    bpm: Float,
    onBpmChange: (Float) -> Unit,
    swing: Float,
    onSwingChange: (Float) -> Unit,
    pattern: List<Int>,
    onToggleStep: (Int, Int) -> Unit,
    mutes: List<Boolean>,
    onMuteToggle: (Int) -> Unit,
    solos: List<Boolean>,
    onSoloToggle: (Int) -> Unit,
    midiMode: Int,
    midiDeviceName: String,
    onMidiModeChange: () -> Unit,
    roll: List<List<Int>>,
    rollLens: List<List<Int>>,
    noteLen: Int,
    onNoteLenCycle: () -> Unit,
    onToggleRollCell: (Int, Int, Int) -> Unit,
    onAudition: (Int, Int) -> Unit,
    playhead: Int,
    flashes: List<Boolean>,
    recording: Boolean,
    onRecToggle: () -> Unit,
    libFiles: List<String>,
    onImport: () -> Unit,
    onPreview: (String) -> Unit,
    onAssign: (Int, String) -> Unit,
    mixAssign: List<Int>,
    onMixAssignCycle: (Int) -> Unit,
    volOf: (Int) -> Float,
    panOf: (Int) -> Float,
    onVol: (Int, Float) -> Unit,
    onPan: (Int, Float) -> Unit,
    masterVol: Float,
    onMasterVol: (Float) -> Unit,
    masterPan: Float,
    onMasterPan: (Float) -> Unit,
    exportBars: Int,
    onExportBarsCycle: () -> Unit,
    exporting: Boolean,
    onExport: () -> Unit,
    selectedPad: Int,
    onSelectPad: (Int) -> Unit,
    peaks: FloatArray,
    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    loopOn: Boolean,
    onLoopToggle: () -> Unit,
    onTrim: () -> Unit,
    onPlayDown: () -> Unit,
    onPlayUp: () -> Unit,
    padPitch: Float,
    onPadPitch: (Float) -> Unit,
    padAttack: Float,
    onPadAttack: (Float) -> Unit,
    padDecay: Float,
    onPadDecay: (Float) -> Unit,
    padSustain: Float,
    onPadSustain: (Float) -> Unit,
    padReleaseMs: Float,
    onPadReleaseMs: (Float) -> Unit,
    padVol: Float,
    onPadVol: (Float) -> Unit,
    padPan: Float,
    onPadPan: (Float) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(
            text = "SP-1200 v3",
            style = MaterialTheme.typography.titleLarge,
            color = Color(0xFF2DD4BF)
        )

        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            SmallButton("PADS", view == 0) { onViewChange(0) }
            SmallButton("SEQ", view == 1) { onViewChange(1) }
            SmallButton("EDIT", view == 2) { onViewChange(2) }
            SmallButton("ROLL", view == 3) { onViewChange(3) }
            SmallButton("LIB", view == 4) { onViewChange(4) }
            SmallButton("MIX", view == 6) { onViewChange(6) }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            SmallButton(if (playing) "STOP" else "PLAY", playing) { onPlayToggle() }
            SmallButton(if (gateMode) "GATE" else "SHOT", gateMode) { onGateModeChange(!gateMode) }
            SmallButton(if (crunch) "12BIT" else "CLEAN", crunch) { onCrunchChange(!crunch) }
            SmallButton(
                when (midiMode) {
                    1 -> "MIDI M"
                    2 -> "MIDI S"
                    else -> "MIDI"
                },
                midiMode != 0
            ) { onMidiModeChange() }
            SmallButton("x$exportBars", false) { onExportBarsCycle() }
            SmallButton(if (exporting) "..." else "EXP", exporting) { onExport() }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            listOf("A", "B", "C", "D").forEachIndexed { i, name ->
                SmallButton(name, bank == i) { onBankChange(i) }
            }
            SmallButton(if (recording) "REC*" else "REC", recording) { onRecToggle() }
        }

        Text(
            text = "MIDI: $midiDeviceName",
            color = Color(0xFF7FA6A3),
            style = MaterialTheme.typography.bodySmall
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "PITCH ${pitch.toInt()} st",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = pitch,
                    onValueChange = onPitchChange,
                    valueRange = -12f..12f,
                    steps = 23
                )
            }

            if (view == 1) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "BPM ${bpm.toInt()}",
                        color = Color.White,
                        style = MaterialTheme.typography.bodySmall
                    )
                    Slider(
                        value = bpm,
                        onValueChange = onBpmChange,
                        valueRange = 60f..180f
                    )
                }

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "SWING ${swing.toInt()}%",
                        color = Color.White,
                        style = MaterialTheme.typography.bodySmall
                    )
                    Slider(
                        value = swing,
                        onValueChange = onSwingChange,
                        valueRange = 0f..50f
                    )
                }
            }
        }

        when (view) {
            1 -> SequencerGrid(
                pattern = pattern,
                onToggleStep = onToggleStep,
                mutes = mutes,
                onMuteToggle = onMuteToggle,
                solos = solos,
                onSoloToggle = onSoloToggle,
                playhead = playhead,
                playing = playing
            )

            2 -> EditorView(
                selectedPad = selectedPad,
                onSelectPad = onSelectPad,
                loadedPads = loadedPads,
                peaks = peaks,
                loopStart = loopStart,
                loopEnd = loopEnd,
                onLoopStart = onLoopStart,
                onLoopEnd = onLoopEnd,
                loopOn = loopOn,
                onLoopToggle = onLoopToggle,
                onTrim = onTrim,
                onPlayDown = onPlayDown,
                onPlayUp = onPlayUp,
                padPitch = padPitch,
                onPadPitch = onPadPitch,
                padAttack = padAttack,
                onPadAttack = onPadAttack,
                padDecay = padDecay,
                onPadDecay = onPadDecay,
                padSustain = padSustain,
                onPadSustain = onPadSustain,
                padReleaseMs = padReleaseMs,
                onPadReleaseMs = onPadReleaseMs,
                padVol = padVol,
                onPadVol = onPadVol,
                padPan = padPan,
                onPadPan = onPadPan
            )

            3 -> Box(modifier = Modifier.fillMaxWidth().weight(1f)) {
                RollView(
                    selectedPad = selectedPad,
                    onSelectPad = onSelectPad,
                    loadedPads = loadedPads,
                    roll = roll,
                    rollLens = rollLens,
                    noteLen = noteLen,
                    onNoteLenCycle = onNoteLenCycle,
                    onToggleRollCell = onToggleRollCell,
                    onAudition = onAudition,
                    playhead = playhead,
                    playing = playing
                )
            }

            4 -> LibView(
                files = libFiles,
                onImport = onImport,
                onPreview = onPreview,
                onAssign = onAssign,
                loadedPads = loadedPads,
                selectedPad = selectedPad,
                onSelectPad = onSelectPad
            )

            6 -> MixView(
                mixAssign = mixAssign,
                onMixAssignCycle = onMixAssignCycle,
                volOf = volOf,
                panOf = panOf,
                onVol = onVol,
                onPan = onPan,
                masterVol = masterVol,
                onMasterVol = onMasterVol,
                masterPan = masterPan,
                onMasterPan = onMasterPan
            )

            else -> {
                Text(
                    text = "Hold = play. Long press = load WAV. Bank: ${'A' + bank}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFF7FA6A3)
                )

                LazyVerticalGrid(
                    columns = GridCells.Fixed(4),
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(16) { index ->
                        Pad(
                            index = index,
                            hasSample = loadedPads.contains(index),
                            flash = flashes[index],
                            onPadDown = onPadDown,
                            onPadUp = onPadUp,
                            onPadLongPress = onPadLongPress
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun LibView(
    files: List<String>,
    onImport: () -> Unit,
    onPreview: (String) -> Unit,
    onAssign: (Int, String) -> Unit,
    loadedPads: Set<Int>,
    selectedPad: Int,
    onSelectPad: (Int) -> Unit
) {
    var armedFile by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (pad in 0 until 16) {
                val bg = when {
                    armedFile != null -> Color(0xFF1B3236)
                    pad == selectedPad -> Color.White
                    loadedPads.contains(pad) -> padColor(pad)
                    else -> Color(0xFF101C1F)
                }

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(34.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(bg)
                        .clickable {
                            val armed = armedFile
                            if (armed != null) {
                                onAssign(pad, armed)
                                armedFile = null
                            } else {
                                onSelectPad(pad)
                            }
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${pad + 1}",
                        color = if (pad == selectedPad) Color.Black else Color.White,
                        fontSize = 8.sp
                    )
                }
            }
        }

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = onImport) { Text("IMPORT") }
            Text(
                text = if (armedFile != null) {
                    "Holding: $armedFile — tap a pad"
                } else {
                    "Tap = play. Hold = pick up, then tap pad"
                },
                color = if (armedFile != null) Color(0xFF2DD4BF) else Color(0xFF7FA6A3),
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1
            )
        }

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .weight(1f),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            items(files.size) { i ->
                val name = files[i]

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(44.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(if (armedFile == name) Color(0xFF2DD4BF) else Color(0xFF152528))
                        .pointerInput(name) {
                            detectTapGestures(
                                onTap = {
                                    if (armedFile == name) {
                                        armedFile = null
                                    } else {
                                        onPreview(name)
                                    }
                                },
                                onLongPress = {
                                    armedFile = name
                                }
                            )
                        },
                    contentAlignment = Alignment.CenterStart
                ) {
                    Text(
                        text = name,
                        color = if (armedFile == name) Color(0xFF06201D) else Color.White,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(horizontal = 12.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun MixView(
    mixAssign: List<Int>,
    onMixAssignCycle: (Int) -> Unit,
    volOf: (Int) -> Float,
    panOf: (Int) -> Float,
    onVol: (Int, Float) -> Unit,
    onPan: (Int, Float) -> Unit,
    masterVol: Float,
    onMasterVol: (Float) -> Unit,
    masterPan: Float,
    onMasterPan: (Float) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "MASTER",
                color = Color(0xFF2DD4BF),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.width(64.dp)
            )
            Column(modifier = Modifier.weight(1f)) {
                Text("VOL ${masterVol.toInt()}%", color = Color.White, fontSize = 9.sp)
                Slider(value = masterVol, onValueChange = onMasterVol, valueRange = 0f..150f)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text("PAN ${masterPan.toInt()}", color = Color.White, fontSize = 9.sp)
                Slider(value = masterPan, onValueChange = onMasterPan, valueRange = 0f..100f)
            }
        }

        for (ch in 0 until 5) {
            val pad = mixAssign[ch]
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(64.dp)
                        .height(40.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFF152528))
                        .clickable { onMixAssignCycle(ch) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "CH${ch + 1}:P${pad + 1}",
                        color = Color.White,
                        fontSize = 9.sp
                    )
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text("VOL ${volOf(pad).toInt()}%", color = Color.White, fontSize = 9.sp)
                    Slider(value = volOf(pad), onValueChange = { onVol(pad, it) }, valueRange = 0f..150f)
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text("PAN ${panOf(pad).toInt()}", color = Color.White, fontSize = 9.sp)
                    Slider(value = panOf(pad), onValueChange = { onPan(pad, it) }, valueRange = 0f..100f)
                }
            }
        }
    }
}

@Composable
fun RollView(
    selectedPad: Int,
    onSelectPad: (Int) -> Unit,
    loadedPads: Set<Int>,
    roll: List<List<Int>>,
    rollLens: List<List<Int>>,
    noteLen: Int,
    onNoteLenCycle: () -> Unit,
    onToggleRollCell: (Int, Int, Int) -> Unit,
    onAudition: (Int, Int) -> Unit,
    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> Color.White
                    loadedPads.contains(pad) -> padColor(pad)
                    else -> Color(0xFF101C1F)
                }

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(30.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(bg)
                        .clickable { onSelectPad(pad) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${pad + 1}",
                        color = if (pad == selectedPad) Color.Black else Color.White,
                        fontSize = 8.sp
                    )
                }
            }
        }

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = onNoteLenCycle) { Text("LEN $noteLen") }
            Text(
                text = "Tap key = hear. Tap cell = note. Tap note = delete",
                color = Color(0xFF7FA6A3),
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1
            )
        }

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .weight(1f),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            items(25) { r ->
                val pitchOff = 12 - r
                val enc = pitchOff + 13

                val row = roll[selectedPad]
                val rowLen = rollLens[selectedPad]

                val cover = IntArray(16) { -1 }
                for (s0 in 0 until 16) {
                    if (row[s0] == enc) {
                        val L = rowLen[s0]
                        for (s in s0 until minOf(16, s0 + L)) {
                            if (cover[s] == -1) cover[s] = s0
                        }
                    }
                }

                val pc = ((pitchOff % 12) + 12) % 12
                val blackKey = pc == 1 || pc == 3 || pc == 6 || pc == 8 || pc == 10

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(2.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .width(26.dp)
                            .height(20.dp)
                            .clip(RoundedCornerShape(3.dp))
                            .background(if (blackKey) Color(0xFF0A1214) else Color(0xFFBFE6E2))
                            .clickable { onAudition(selectedPad, pitchOff) },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = if (pitchOff >= 0) "+$pitchOff" else "$pitchOff",
                            color = if (blackKey) Color.White else Color.Black,
                            fontSize = 7.sp
                        )
                    }

                    for (step in 0 until 16) {
                        val isNote = cover[step] >= 0
                        val isStart = cover[step] == step

                        val bg = when {
                            isNote -> padColor(selectedPad)
                            playing && step == playhead -> Color(0xFF27464B)
                            step % 4 == 0 -> Color(0xFF1B3236)
                            else -> Color(0xFF0F1B1E)
                        }

                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .height(20.dp)
                                .clip(RoundedCornerShape(2.dp))
                                .background(bg)
                                .clickable {
                                    onToggleRollCell(selectedPad, step, enc)
                                }
                        ) {
                            if (isStart) {
                                Box(
                                    modifier = Modifier
                                        .fillMaxHeight()
                                        .width(3.dp)
                                        .background(Color(0xFFFFFFFF))
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SequencerGrid(
    pattern: List<Int>,
    onToggleStep: (Int, Int) -> Unit,
    mutes: List<Boolean>,
    onMuteToggle: (Int) -> Unit,
    solos: List<Boolean>,
    onSoloToggle: (Int) -> Unit,
    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        for (pad in 0 until 16) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(3.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(26.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (mutes[pad]) Color(0xFFB71C1C) else Color(0xFF152528))
                        .clickable { onMuteToggle(pad) },
                    contentAlignment = Alignment.Center
                ) {
                    Text("M", color = Color.White, style = MaterialTheme.typography.bodySmall)
                }

                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(26.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (solos[pad]) Color(0xFFFDD835) else Color(0xFF152528))
                        .clickable { onSoloToggle(pad) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        "S",
                        color = if (solos[pad]) Color.Black else Color.White,
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                for (step in 0 until 16) {
                    val on = (pattern[pad] ushr step) and 1 == 1
                    val offColor = when {
                        playing && step == playhead -> Color(0xFF27464B)
                        step % 4 == 0 -> Color(0xFF1B3236)
                        else -> Color(0xFF0F1B1E)
                    }

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(26.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(if (on) padColor(pad) else offColor)
                            .clickable { onToggleStep(pad, step) }
                    )
                }
            }
        }
    }
}

@Composable
fun EditorView(
    selectedPad: Int,
    onSelectPad: (Int) -> Unit,
    loadedPads: Set<Int>,
    peaks: FloatArray,
    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    loopOn: Boolean,
    onLoopToggle: () -> Unit,
    onTrim: () -> Unit,
    onPlayDown: () -> Unit,
    onPlayUp: () -> Unit,
    padPitch: Float,
    onPadPitch: (Float) -> Unit,
    padAttack: Float,
    onPadAttack: (Float) -> Unit,
    padDecay: Float,
    onPadDecay: (Float) -> Unit,
    padSustain: Float,
    onPadSustain: (Float) -> Unit,
    padReleaseMs: Float,
    onPadReleaseMs: (Float) -> Unit,
    padVol: Float,
    onPadVol: (Float) -> Unit,
    padPan: Float,
    onPadPan: (Float) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> Color.White
                    loadedPads.contains(pad) -> padColor(pad)
                    else -> Color(0xFF101C1F)
                }

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(30.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(bg)
                        .clickable { onSelectPad(pad) },
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${pad + 1}",
                        color = if (pad == selectedPad) Color.Black else Color.White,
                        fontSize = 8.sp
                    )
                }
            }
        }

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(100.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0xFF0F1B1E))
        ) {
            val w = size.width
            val h = size.height

            if (peaks.isNotEmpty()) {
                val lx = loopStart / 100f * w
                val rx = loopEnd / 100f * w

                drawRect(
                    color = Color(0x33FFFFFF),
                    topLeft = Offset(lx, 0f),
                    size = Size(rx - lx, h)
                )

                val n = peaks.size
                val barW = w / n

                for (i in 0 until n) {
                    val x = (i + 0.5f) * w / n
                    val p = peaks[i].coerceIn(0f, 1f) * (h / 2f)

                    drawLine(
                        color = Color(0xFF2DD4BF),
                        start = Offset(x, h / 2f - p),
                        end = Offset(x, h / 2f + p),
                        strokeWidth = barW
                    )
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "LOOP START ${loopStart.toInt()}%",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = loopStart,
                    onValueChange = onLoopStart,
                    valueRange = 0f..100f
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "LOOP END ${loopEnd.toInt()}%",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = loopEnd,
                    onValueChange = onLoopEnd,
                    valueRange = 0f..100f
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "PITCH ${padPitch.toInt()} st",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padPitch,
                    onValueChange = onPadPitch,
                    valueRange = -12f..12f,
                    steps = 23
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "ATTACK ${padAttack.toInt()} ms",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padAttack,
                    onValueChange = onPadAttack,
                    valueRange = 0f..500f
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "DECAY ${padDecay.toInt()} ms",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padDecay,
                    onValueChange = onPadDecay,
                    valueRange = 0f..1000f
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "SUSTAIN ${padSustain.toInt()}%",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padSustain,
                    onValueChange = onPadSustain,
                    valueRange = 0f..100f
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "VOL ${padVol.toInt()}%",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padVol,
                    onValueChange = onPadVol,
                    valueRange = 0f..150f
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "PAN ${padPan.toInt()}",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padPan,
                    onValueChange = onPadPan,
                    valueRange = 0f..100f
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "RELEASE ${padReleaseMs.toInt()} ms",
                    color = Color.White,
                    style = MaterialTheme.typography.bodySmall
                )
                Slider(
                    value = padReleaseMs,
                    onValueChange = onPadReleaseMs,
                    valueRange = 0f..1000f
                )
            }

            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(onClick = onLoopToggle) {
                    Text(if (loopOn) "LOOP ON" else "LOOP OFF")
                }

                Button(onClick = onTrim) {
                    Text("TRIM")
                }
            }
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0xFF2DD4BF))
                .pointerInput(Unit) {
                    detectTapGestures(
                        onPress = {
                            onPlayDown()
                            tryAwaitRelease()
                            onPlayUp()
                        }
                    )
                },
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "PLAY (hold)",
                color = Color(0xFF06201D),
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}

@Composable
fun Pad(
    index: Int,
    hasSample: Boolean,
    flash: Boolean,
    onPadDown: (Int) -> Unit,
    onPadUp: (Int) -> Unit,
    onPadLongPress: (Int) -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .clip(RoundedCornerShape(20.dp))
            .background(if (flash) Color.White else padColor(index))
            .pointerInput(index) {
                detectTapGestures(
                    onPress = {
                        onPadDown(index)
                        tryAwaitRelease()
                        onPadUp(index)
                    },
                    onLongPress = {
                        onPadLongPress(index)
                    }
                )
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = if (hasSample) "WAV ${index + 1}" else "PAD ${index + 1}",
            color = Color.Black,
            style = MaterialTheme.typography.titleMedium
        )
    }
}
