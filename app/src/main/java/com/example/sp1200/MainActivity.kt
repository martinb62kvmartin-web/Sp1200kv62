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
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.window.Dialog
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.ui.graphics.toArgb
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import android.graphics.BitmapFactory
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.json.JSONArray
import org.json.JSONObject

private val thBg = mutableStateOf(Color(0xFF0F1418))
private val thCy = mutableStateOf(Color(0xFF29C5F6))
private val thPk = mutableStateOf(Color(0xFFE9255B))
private val thWv = mutableStateOf(Color(0xFFA62645))
private val thDk = mutableStateOf(Color(0xFF241B3F))

val C_BG: Color @Composable get() = thBg.value
val C_CYAN: Color @Composable get() = thCy.value
val C_PINK: Color @Composable get() = thPk.value
val C_WAVEBG: Color @Composable get() = thWv.value
val C_DARK: Color @Composable get() = thDk.value

fun themeGet(i: Int): Color = when (i) {
    0 -> thBg.value
    1 -> thCy.value
    2 -> thPk.value
    3 -> thWv.value
    else -> thDk.value
}

fun themeSet(i: Int, c: Color) {
    when (i) {
        0 -> thBg.value = c
        1 -> thCy.value = c
        2 -> thPk.value = c
        3 -> thWv.value = c
        else -> thDk.value = c
    }
}

val PALETTE = listOf(
    Color(0xFF0F1418), Color(0xFF241B3F), Color(0xFF29C5F6), Color(0xFFE9255B),
    Color(0xFFA62645), Color(0xFF2DD4BF), Color(0xFFFBBF24), Color(0xFFA3E635),
    Color(0xFF38BDF8), Color(0xFFC084FC), Color(0xFFF472B6), Color(0xFF101C1F),
    Color(0xFFFFFFFF), Color(0xFF000000), Color(0xFF7FA6A3), Color(0xFFF0A45C)
)

const val ROLL_STEPS = 64
const val ROLL_PITCHES = 25

data class RollPoint(val step: Int, val pitch: Int)
data class RollNote(val step: Int, val pitch: Int, val len: Int, val velocity: Int)

enum class RollTool { DRAW, SELECT, ERASE, VELOCITY, RESIZE }

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
    private external fun nativeClearPad(padIndex: Int)
    private external fun nativeSetPadReverse(padIndex: Int, enabled: Boolean)
    private external fun nativeSetPadStretch(padIndex: Int, steps: Int)
    private external fun nativeNormalizePad(padIndex: Int): Boolean
    private external fun nativeTrimSilencePad(padIndex: Int): Boolean
    private external fun nativeMakeMonoPad(padIndex: Int): Boolean
    private external fun nativeBouncePad(padIndex: Int): Boolean
    private external fun nativeAutoChop(padIndex: Int): Int
    private external fun nativeSplitStems(padIndex: Int): Int
    private external fun nativeSeqSetPlaying(playing: Boolean)
    private external fun nativeSeqSetBpm(bpm: Float)
    private external fun nativeSeqSetSwing(swing: Float)
    private external fun nativeSeqSetMask(padIndex: Int, mask: Int)
    private external fun nativeSetRoll(padIndex: Int, step: Int, value: Int, len: Int)
    private external fun nativeSetRollVel(padIndex: Int, step: Int, vel: Int)
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
    private external fun nativeGetLevels(): FloatArray
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
    private var rollBanks by mutableStateOf(List(4) { List(16) { List(ROLL_STEPS) { 0 } } })
    private var rollLenBanks by mutableStateOf(List(4) { List(16) { List(ROLL_STEPS) { 0 } } })
    private var velBanks by mutableStateOf(List(4) { List(16) { List(ROLL_STEPS) { 100 } } })
    private var noteLen by mutableStateOf(1)
    private var mutes by mutableStateOf(List(16) { false })
    private var solos by mutableStateOf(List(16) { false })
    private var midiMode by mutableStateOf(0)
    private var midiDeviceName by mutableStateOf("none")
    private var recording by mutableStateOf(false)
    private var playhead by mutableStateOf(0)
    private var pollTick by mutableStateOf(0)
    private var hitTimes by mutableStateOf(List(16) { 0L })
    private var levels by mutableStateOf(FloatArray(18))
    private var libFiles by mutableStateOf(listOf<String>())
    private var mixAssign by mutableStateOf(List(5) { it })
    private var volBanks by mutableStateOf(List(16) { 100f })
    private var panBanks by mutableStateOf(List(16) { 50f })
    private var masterVol by mutableStateOf(100f)
    private var masterPan by mutableStateOf(50f)
    private var exportBars by mutableStateOf(2)
    private var exporting by mutableStateOf(false)
    private var exportWasPlaying = false
    private var reverseBanks by mutableStateOf(List(4) { List(16) { false } })
    private var stretchBanks by mutableStateOf(List(4) { List(16) { 0 } })
    private var toneBanks by mutableStateOf(List(4) { List(16) { 50f } })
    private var padLabels by mutableStateOf(List(4) { List(16) { "" } })
    private var wallFx by mutableStateOf(0)
    private var wallBitmap by mutableStateOf<ImageBitmap?>(null)
    private var padPeaks by mutableStateOf(List(16) { FloatArray(0) })

    private var selectedPad by mutableStateOf(0)
    private var peaks by mutableStateOf(FloatArray(0))

    private data class RollSnapshot(
        val roll: List<List<List<Int>>>,
        val lens: List<List<List<Int>>>,
        val velocities: List<List<List<Int>>>
    )

    private val rollUndo = java.util.ArrayDeque<RollSnapshot>()
    private val rollRedo = java.util.ArrayDeque<RollSnapshot>()

    private fun copyRollState() = RollSnapshot(
        rollBanks.map { rows -> rows.map { it.toList() } },
        rollLenBanks.map { rows -> rows.map { it.toList() } },
        velBanks.map { rows -> rows.map { it.toList() } }
    )

    private fun recordRollEdit() {
        rollUndo.addLast(copyRollState())
        while (rollUndo.size > 64) rollUndo.removeFirst()
        rollRedo.clear()
    }

    private fun syncRollBankToNative(targetBank: Int = bank) {
        nativeSetBank(targetBank)
        for (pad in 0 until 16) {
            for (step in 0 until ROLL_STEPS) {
                nativeSetRoll(pad, step, rollBanks[targetBank][pad][step], rollLenBanks[targetBank][pad][step])
                nativeSetRollVel(pad, step, velBanks[targetBank][pad][step])
            }
        }
        nativeSetBank(bank)
    }

    private fun undoRollEdit() {
        if (rollUndo.isEmpty()) return
        rollRedo.addLast(copyRollState())
        val snapshot = rollUndo.removeLast()
        rollBanks = snapshot.roll
        rollLenBanks = snapshot.lens
        velBanks = snapshot.velocities
        syncRollBankToNative()
    }

    private fun redoRollEdit() {
        if (rollRedo.isEmpty()) return
        rollUndo.addLast(copyRollState())
        val snapshot = rollRedo.removeLast()
        rollBanks = snapshot.roll
        rollLenBanks = snapshot.lens
        velBanks = snapshot.velocities
        syncRollBankToNative()
    }

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

    private fun refreshPadPeaks() {
        padPeaks = (0 until 16).map { i ->
            if (loadedBanks[bank].contains(i)) nativeGetPeaks(i, 48) else FloatArray(0)
        }
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
                    refreshPadPeaks()
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
                refreshPadPeaks()
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

                val velArr = JSONArray()
                for (p in 0 until 16) {
                    velArr.put(JSONArray(velBanks[b][p]))
                }
                bo.put("vel", velArr)

                val revArr = JSONArray()
                for (p in 0 until 16) {
                    revArr.put(reverseBanks[b][p])
                }
                bo.put("rev", revArr)

                val stArr = JSONArray()
                for (p in 0 until 16) {
                    stArr.put(stretchBanks[b][p])
                }
                bo.put("stretch", stArr)

                val toneArr = JSONArray()
                for (p in 0 until 16) {
                    toneArr.put(toneBanks[b][p])
                }
                bo.put("tone", toneArr)

                val labArr = JSONArray()
                for (p in 0 until 16) {
                    labArr.put(padLabels[b][p])
                }
                bo.put("labels", labArr)

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

            root.put("lenscale", 4)
            root.put("rollsteps", ROLL_STEPS)

            val thArr = JSONArray()
            for (i in 0 until 5) {
                thArr.put(themeGet(i).toArgb().toLong() and 0xFFFFFFFFL)
            }
            root.put("theme", thArr)
            root.put("wallfx", wallFx)

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
            wallFx = root.optInt("wallfx", 0)

            root.optJSONArray("theme")?.let { ta ->
                for (i in 0 until minOf(5, ta.length())) {
                    themeSet(i, Color(ta.optLong(i, 0L).toInt()))
                }
            }

            val banksArr = root.optJSONArray("banks") ?: return

            val newPatterns = patternBanks.toMutableList()
            val newRolls = rollBanks.toMutableList()
            val newRollLens = rollLenBanks.toMutableList()
            val newVels = velBanks.toMutableList()
            val newRev = reverseBanks.toMutableList()
            val newStretch = stretchBanks.toMutableList()
            val newTone = toneBanks.toMutableList()
            val newLabels = padLabels.toMutableList()
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
                        rows[p] = (0 until ROLL_STEPS).map { idx -> st.optInt(idx, 0) }
                    }
                    newRolls[b] = rows
                }

                bo.optJSONArray("rolllen")?.let { ra ->
                    val rows = rollLenBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ra.length())) {
                        val st = ra.optJSONArray(p) ?: continue
                        rows[p] = (0 until ROLL_STEPS).map { idx -> st.optInt(idx, 0) }
                    }
                    newRollLens[b] = rows
                }

                bo.optJSONArray("vel")?.let { va2 ->
                    val rows = velBanks[b].toMutableList()
                    for (p in 0 until minOf(16, va2.length())) {
                        val st = va2.optJSONArray(p) ?: continue
                        rows[p] = (0 until ROLL_STEPS).map { idx -> st.optInt(idx, 100) }
                    }
                    newVels[b] = rows
                }

                bo.optJSONArray("rev")?.let { rv ->
                    newRev[b] = (0 until 16).map { rv.optBoolean(it, false) }
                }

                bo.optJSONArray("stretch")?.let { sta ->
                    val rows = stretchBanks[b].toMutableList()
                    for (p in 0 until minOf(16, sta.length())) {
                        rows[p] = sta.optInt(p, 0)
                    }
                    newStretch[b] = rows
                }

                bo.optJSONArray("tone")?.let { ta ->
                    val rows = toneBanks[b].toMutableList()
                    for (p in 0 until minOf(16, ta.length())) {
                        rows[p] = ta.optDouble(p, 50.0).toFloat()
                    }
                    newTone[b] = rows
                }

                bo.optJSONArray("labels")?.let { la2 ->
                    val rows = padLabels[b].toMutableList()
                    for (p in 0 until minOf(16, la2.length())) {
                        rows[p] = la2.optString(p, "")
                    }
                    newLabels[b] = rows
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
            val lsOld = root.optInt("lenscale", 1)
            if (lsOld < 4) {
                val mult = 4 / lsOld
                for (b2 in 0 until 4) {
                    newRollLens[b2] = newRollLens[b2].map { row -> row.map { it * mult } }
                }
            }
            rollLenBanks = newRollLens
            velBanks = newVels
            reverseBanks = newRev
            stretchBanks = newStretch
            toneBanks = newTone
            padLabels = newLabels
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
                for (st in 0 until ROLL_STEPS) {
                    nativeSetRoll(p, st, rollBanks[b][p][st], rollLenBanks[b][p][st])
                    nativeSetRollVel(p, st, velBanks[b][p][st])
                }
                nativeSetLoopPoints(p, loopStartBanks[b][p] / 100f, loopEndBanks[b][p] / 100f)
                nativeSetLoopOn(p, loopOnBanks[b][p])
                nativeSetPadReverse(p, reverseBanks[b][p])
                nativeSetPadStretch(p, stretchBanks[b][p])
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

    private val wallLauncher =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            if (uri == null) return@registerForActivityResult
            try {
                val target = File(filesDir, "wallpaper.png")
                contentResolver.openInputStream(uri)?.use { ins ->
                    target.outputStream().use { outs -> ins.copyTo(outs) }
                }
                wallBitmap = BitmapFactory.decodeFile(target.absolutePath)?.asImageBitmap()
            } catch (_: Exception) {
            }
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
                        refreshPadPeaks()
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
        refreshPadPeaks()
        peaks = nativeGetPeaks(selectedPad, 200)

        val wf = File(filesDir, "wallpaper.png")
        if (wf.exists()) {
            wallBitmap = BitmapFactory.decodeFile(wf.absolutePath)?.asImageBitmap()
        }

        midiManager = getSystemService(MIDI_SERVICE) as MidiManager

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = C_BG
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
                        bank = bank,
                        onBankChange = { b ->
                            bank = b
                            nativeSetBank(b)
                            peaks = nativeGetPeaks(selectedPad, 200)
                            refreshPadPeaks()
                        },
                        view = view,
                        onViewChange = { view = it },
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
                        vels = velBanks[bank],
                        onVel = { pad, st, d ->
                            if (st in 0 until ROLL_STEPS) {
                                val cur = velBanks[bank][pad][st]
                                val next = (cur + d.toInt()).coerceIn(10, 150)
                                if (next != cur) {
                                    recordRollEdit()
                                    velBanks = velBanks.set2(bank, pad, velBanks[bank][pad].toMutableList().also { it[st] = next })
                                    nativeSetRollVel(pad, st, next)
                                }
                            }
                        },
                        onResizeDelta = { pad, st, d ->
                            if (st in 0 until ROLL_STEPS) {
                                val cur = rollLenBanks[bank][pad][st]
                                val next = (cur + d).coerceIn(1, (ROLL_STEPS - st) * 4)
                                if (next != cur) {
                                    recordRollEdit()
                                    rollLenBanks = rollLenBanks.set2(bank, pad, rollLenBanks[bank][pad].toMutableList().also { it[st] = next })
                                    nativeSetRoll(pad, st, rollBanks[bank][pad][st], next)
                                }
                            }
                        },
                        onDeleteRoll = { pad, st ->
                            if (st in 0 until ROLL_STEPS) {
                                recordRollEdit()
                                rollBanks = rollBanks.set2(bank, pad, rollBanks[bank][pad].toMutableList().also { it[st] = 0 })
                                rollLenBanks = rollLenBanks.set2(bank, pad, rollLenBanks[bank][pad].toMutableList().also { it[st] = 0 })
                                nativeSetRoll(pad, st, 0, 1)
                            }
                        },
                        onDeleteNote = { pad, st, pitchIndex ->
                            if (st in 0 until ROLL_STEPS && pitchIndex in 0 until ROLL_PITCHES) {
                                val bit = 1 shl pitchIndex
                                val cur = rollBanks[bank][pad][st]
                                if ((cur and bit) != 0) {
                                    recordRollEdit()
                                    val next = cur and bit.inv()
                                    rollBanks = rollBanks.set2(bank, pad, rollBanks[bank][pad].toMutableList().also { it[st] = next })
                                    if (next == 0) rollLenBanks = rollLenBanks.set2(bank, pad, rollLenBanks[bank][pad].toMutableList().also { it[st] = 0 })
                                    nativeSetRoll(pad, st, next, if (next == 0) 1 else rollLenBanks[bank][pad][st])
                                }
                            }
                        },
                        onMoveNote = { pad, fromStep, fromPitch, toStep, toPitch ->
                            if (fromStep in 0 until ROLL_STEPS && toStep in 0 until ROLL_STEPS && fromPitch in 0 until ROLL_PITCHES && toPitch in 0 until ROLL_PITCHES) {
                                val fromBit = 1 shl fromPitch
                                val sourceMask = rollBanks[bank][pad][fromStep]
                                if ((sourceMask and fromBit) != 0 && (fromStep != toStep || fromPitch != toPitch)) {
                                    recordRollEdit()
                                    val rows = rollBanks[bank][pad].toMutableList()
                                    val lens = rollLenBanks[bank][pad].toMutableList()
                                    val velocities = velBanks[bank][pad].toMutableList()
                                    val len = lens[fromStep].coerceIn(1, (ROLL_STEPS - toStep) * 4)
                                    rows[fromStep] = rows[fromStep] and fromBit.inv()
                                    if (rows[fromStep] == 0) lens[fromStep] = 0
                                    val toBit = 1 shl toPitch
                                    rows[toStep] = rows[toStep] or toBit
                                    lens[toStep] = maxOf(lens[toStep], len)
                                    velocities[toStep] = velocities[fromStep]
                                    rollBanks = rollBanks.set2(bank, pad, rows)
                                    rollLenBanks = rollLenBanks.set2(bank, pad, lens)
                                    velBanks = velBanks.set2(bank, pad, velocities)
                                    nativeSetRoll(pad, fromStep, rows[fromStep], if (rows[fromStep] == 0) 1 else lens[fromStep])
                                    nativeSetRoll(pad, toStep, rows[toStep], lens[toStep])
                                    nativeSetRollVel(pad, toStep, velocities[toStep])
                                }
                            }
                        },
                        onPasteNotes = { pad, anchorStep, anchorPitch, notes ->
                            if (notes.isNotEmpty()) {
                                recordRollEdit()
                                val rows = rollBanks[bank][pad].toMutableList()
                                val lens = rollLenBanks[bank][pad].toMutableList()
                                val velocities = velBanks[bank][pad].toMutableList()
                                notes.forEach { note ->
                                    val st = (anchorStep + note.step).coerceIn(0, ROLL_STEPS - 1)
                                    val pi = (anchorPitch + note.pitch).coerceIn(0, ROLL_PITCHES - 1)
                                    rows[st] = rows[st] or (1 shl pi)
                                    lens[st] = maxOf(lens[st], note.len.coerceIn(1, (ROLL_STEPS - st) * 4))
                                    velocities[st] = note.velocity.coerceIn(10, 150)
                                }
                                rollBanks = rollBanks.set2(bank, pad, rows)
                                rollLenBanks = rollLenBanks.set2(bank, pad, lens)
                                velBanks = velBanks.set2(bank, pad, velocities)
                                for (st in 0 until ROLL_STEPS) {
                                    nativeSetRoll(pad, st, rows[st], lens[st])
                                    nativeSetRollVel(pad, st, velocities[st])
                                }
                            }
                        },
                        onQuantize = { pad, points, grid ->
                            val source = if (points.isEmpty()) {
                                (0 until ROLL_STEPS).flatMap { st -> (0 until ROLL_PITCHES).filter { pi -> (rollBanks[bank][pad][st] and (1 shl pi)) != 0 }.map { pi -> RollPoint(st, pi) } }
                            } else points.toList()
                            val notes = source.mapNotNull { point ->
                                if (point.step !in 0 until ROLL_STEPS || point.pitch !in 0 until ROLL_PITCHES || (rollBanks[bank][pad][point.step] and (1 shl point.pitch)) == 0) null else RollNote(point.step, point.pitch, rollLenBanks[bank][pad][point.step], velBanks[bank][pad][point.step])
                            }
                            if (notes.isNotEmpty()) {
                                recordRollEdit()
                                val rows = rollBanks[bank][pad].toMutableList()
                                val lens = rollLenBanks[bank][pad].toMutableList()
                                notes.forEach { n -> rows[n.step] = rows[n.step] and (1 shl n.pitch).inv() }
                                for (st in 0 until ROLL_STEPS) if (rows[st] == 0) lens[st] = 0
                                notes.forEach { n -> val target = (kotlin.math.round(n.step.toDouble() / grid) * grid).toInt().coerceIn(0, ROLL_STEPS - 1); rows[target] = rows[target] or (1 shl n.pitch); lens[target] = maxOf(lens[target], n.len.coerceIn(1, (ROLL_STEPS - target) * 4)) }
                                rollBanks = rollBanks.set2(bank, pad, rows)
                                rollLenBanks = rollLenBanks.set2(bank, pad, lens)
                                for (st in 0 until ROLL_STEPS) nativeSetRoll(pad, st, rows[st], lens[st])
                            }
                        },
                        onTranspose = { pad, points, delta ->
                            val source = if (points.isEmpty()) {
                                (0 until ROLL_STEPS).flatMap { st -> (0 until ROLL_PITCHES).filter { pi -> (rollBanks[bank][pad][st] and (1 shl pi)) != 0 }.map { pi -> RollPoint(st, pi) } }
                            } else points.toList()
                            val notes = source.mapNotNull { point ->
                                if (point.step !in 0 until ROLL_STEPS || point.pitch !in 0 until ROLL_PITCHES || (rollBanks[bank][pad][point.step] and (1 shl point.pitch)) == 0) null else RollNote(point.step, point.pitch, rollLenBanks[bank][pad][point.step], velBanks[bank][pad][point.step])
                            }
                            if (notes.isNotEmpty()) {
                                recordRollEdit()
                                val rows = rollBanks[bank][pad].toMutableList()
                                val lens = rollLenBanks[bank][pad].toMutableList()
                                notes.forEach { n -> rows[n.step] = rows[n.step] and (1 shl n.pitch).inv() }
                                for (st in 0 until ROLL_STEPS) if (rows[st] == 0) lens[st] = 0
                                notes.forEach { n -> val pi = (n.pitch + delta).coerceIn(0, ROLL_PITCHES - 1); rows[n.step] = rows[n.step] or (1 shl pi); lens[n.step] = maxOf(lens[n.step], n.len) }
                                rollBanks = rollBanks.set2(bank, pad, rows)
                                rollLenBanks = rollLenBanks.set2(bank, pad, lens)
                                for (st in 0 until ROLL_STEPS) nativeSetRoll(pad, st, rows[st], lens[st])
                            }
                        },
                        onClearRoll = { pad ->
                            recordRollEdit()
                            rollBanks = rollBanks.set2(bank, pad, List(ROLL_STEPS) { 0 })
                            rollLenBanks = rollLenBanks.set2(bank, pad, List(ROLL_STEPS) { 0 })
                            for (st in 0 until ROLL_STEPS) nativeSetRoll(pad, st, 0, 1)
                        },
                        onUndo = { undoRollEdit() },
                        onRedo = { redoRollEdit() },
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
                                4 -> 8
                                8 -> 16
                                16 -> 32
                                else -> 1
                            }
                        },
                        onToggleRollCell = { pad, step, enc ->
                            if (step in 0 until ROLL_STEPS && enc in 0 until ROLL_PITCHES) {
                            recordRollEdit()
                            val cur = rollBanks[bank][pad][step]
                            val bit = 1 shl enc
                            if ((cur and bit) != 0) {
                                val nm = cur and bit.inv()
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[step] = nm }
                                )
                                if (nm == 0) {
                                    rollLenBanks = rollLenBanks.set2(
                                        bank, pad,
                                        rollLenBanks[bank][pad].toMutableList().also { it[step] = 0 }
                                    )
                                    nativeSetRoll(pad, step, 0, 1)
                                } else {
                                    nativeSetRoll(pad, step, nm, rollLenBanks[bank][pad][step])
                                }
                            } else {
                                val nm = cur or bit
                                rollBanks = rollBanks.set2(
                                    bank, pad,
                                    rollBanks[bank][pad].toMutableList().also { it[step] = nm }
                                )
                                if (cur == 0) {
                                    rollLenBanks = rollLenBanks.set2(
                                        bank, pad,
                                        rollLenBanks[bank][pad].toMutableList().also { it[step] = noteLen }
                                    )
                                }
                                nativeSetRoll(pad, step, nm, if (cur == 0) noteLen else rollLenBanks[bank][pad][step])
                            }
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
                        levels = levels,
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
                        padPeaks = padPeaks,
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
                                refreshPadPeaks()
                                Toast.makeText(this, "Trimmed", Toast.LENGTH_SHORT).show()
                            }
                        },
                        onDelete = {
                            nativeClearPad(selectedPad)
                            loadedBanks = loadedBanks.toMutableList().also {
                                it[bank] = it[bank] - selectedPad
                            }
                            peaks = FloatArray(0)
                            refreshPadPeaks()
                        },
                        reverse = reverseBanks[bank][selectedPad],
                        onReverseToggle = {
                            val v = !reverseBanks[bank][selectedPad]
                            reverseBanks = reverseBanks.set2(bank, selectedPad, v)
                            nativeSetPadReverse(selectedPad, v)
                        },
                        padPitch = pitchBanks[bank][selectedPad],
                        onPadPitch = { value ->
                            pitchBanks = pitchBanks.set2(bank, selectedPad, value)
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
                        },
                        pollTick = pollTick,
                        stretch = stretchBanks[bank][selectedPad],
                        onStretch = { v ->
                            stretchBanks = stretchBanks.set2(bank, selectedPad, v)
                            nativeSetPadStretch(selectedPad, v)
                        },
                        padAttack = attackBanks[bank][selectedPad],
                        onPadAttack = { value ->
                            attackBanks = attackBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padRelease = releaseBanks[bank][selectedPad],
                        onPadRelease = { value ->
                            releaseBanks = releaseBanks.set2(bank, selectedPad, value)
                            pushPadParams(selectedPad)
                        },
                        padTone = toneBanks[bank][selectedPad],
                        onPadTone = { value ->
                            toneBanks = toneBanks.set2(bank, selectedPad, value)
                        },
                        onTool = { name ->
                            when (name) {
                                "NORMALIZE" -> {
                                    nativeNormalizePad(selectedPad)
                                    peaks = nativeGetPeaks(selectedPad, 200)
                                    refreshPadPeaks()
                                }
                                "TRIM SILENCE" -> {
                                    nativeTrimSilencePad(selectedPad)
                                    peaks = nativeGetPeaks(selectedPad, 200)
                                    refreshPadPeaks()
                                }
                                "MAKE MONO" -> {
                                    nativeMakeMonoPad(selectedPad)
                                    Toast.makeText(this, "Mono OK", Toast.LENGTH_SHORT).show()
                                }
                                "BOUNCE" -> {
                                    nativeBouncePad(selectedPad)
                                    peaks = nativeGetPeaks(selectedPad, 200)
                                    refreshPadPeaks()
                                    Toast.makeText(this, "Bounced 12bit", Toast.LENGTH_SHORT).show()
                                }
                                "AUTO-CHOP" -> {
                                    val n = nativeAutoChop(selectedPad)
                                    if (n > 0) {
                                        loadedBanks = loadedBanks.toMutableList().also {
                                            it[bank] = (0 until 16).toSet()
                                        }
                                        refreshPadPeaks()
                                        Toast.makeText(this, "Chopped to 16 pads", Toast.LENGTH_SHORT).show()
                                    }
                                }
                                "SPLIT STEMS" -> {
                                    val n = nativeSplitStems(selectedPad)
                                    if (n > 0) {
                                        loadedBanks = loadedBanks.toMutableList().also {
                                            it[bank] = it[bank] + selectedPad + ((selectedPad + 1) % 16)
                                        }
                                        refreshPadPeaks()
                                        Toast.makeText(this, "Low/High split done", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            }
                        },
                        labels = padLabels[bank],
                        onLabel = { text ->
                            padLabels = padLabels.set2(bank, selectedPad, text)
                        },
                        onPreviewPad = { nativeTriggerPad(selectedPad) },
                        wall = wallBitmap,
                        wallFx = wallFx,
                        onLoadWallpaper = { wallLauncher.launch(arrayOf("image/*")) },
                        onWallFx = { wallFx = (wallFx + 1) % 4 },
                        onClearWallpaper = {
                            wallBitmap = null
                            File(filesDir, "wallpaper.png").delete()
                        },
                        crunch = crunch,
                        onCrunchChange = { enabled ->
                            crunch = enabled
                            nativeSetCrunch(enabled)
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
                levels = nativeGetLevels()

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

@Composable
fun KBtn(
    label: String,
    active: Boolean = false,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(if (active) C_PINK else Color.White)
            .clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            color = if (active) Color.White else C_PINK,
            fontWeight = FontWeight.Bold,
            fontSize = 11.sp,
            maxLines = 1
        )
    }
}

@Composable
fun RowScope.TabBtn(
    label: String,
    active: Boolean,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .weight(1f)
            .height(38.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(if (active) C_PINK else C_DARK)
            .clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            color = Color.White,
            fontWeight = FontWeight.Bold,
            fontSize = 10.sp,
            maxLines = 1
        )
    }
}

@Composable
fun Fader(
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    onValueChange: (Float) -> Unit,
    modifier: Modifier = Modifier
) {
    val span = range.endInclusive - range.start
    val frac = ((value - range.start) / span).coerceIn(0f, 1f)
    val cur = rememberUpdatedState(value)
    val startVal = remember { mutableStateOf(0f) }
    val acc = remember { mutableStateOf(0f) }

    BoxWithConstraints(
        modifier = modifier
            .height(30.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(C_DARK)
            .pointerInput(range.start, range.endInclusive) {
                detectDragGestures(
                    onDragStart = {
                        startVal.value = cur.value
                        acc.value = 0f
                    }
                ) { change, drag ->
                    change.consume()
                    acc.value += drag.x / size.width.toFloat() * span
                    onValueChange((startVal.value + acc.value).coerceIn(range))
                }
            }
    ) {
        val w = constraints.maxWidth
        val x = (frac * (w - 20)).toInt()

        Box(
            modifier = Modifier
                .offset { IntOffset(x, 0) }
                .width(20.dp)
                .fillMaxHeight()
                .background(C_CYAN)
        )
    }
}

@Composable
fun Knob(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    onValueChange: (Float) -> Unit
) {
    val span = range.endInclusive - range.start
    val frac = ((value - range.start) / span).coerceIn(0f, 1f)
    val valueNow = rememberUpdatedState(value)
    val knobStart = remember { mutableStateOf(0f) }
    val knobAcc = remember { mutableStateOf(0f) }

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(62.dp)
                .clip(CircleShape)
                .background(Color.White)
                .pointerInput(range.start, range.endInclusive) {
                    detectDragGestures(
                        onDragStart = {
                            knobStart.value = valueNow.value
                            knobAcc.value = 0f
                        }
                    ) { change, drag ->
                        change.consume()
                        knobAcc.value -= drag.y / 200f * span
                        onValueChange((knobStart.value + knobAcc.value).coerceIn(range))
                    }
                },
            contentAlignment = Alignment.Center
        ) {
            Box(
                modifier = Modifier
                    .rotate(-135f + frac * 270f)
                    .width(3.dp)
                    .height(24.dp)
                    .offset(y = (-15).dp)
                    .background(Color.Black)
            )
        }
        Text(label, color = C_PINK, fontWeight = FontWeight.Bold, fontSize = 10.sp)
    }
}

@Composable
fun Wave(
    peaks: FloatArray,
    bg: Color,
    line: Color,
    shake: Int,
    modifier: Modifier = Modifier
) {
    Canvas(modifier.background(bg)) {
        val n = peaks.size
        if (n > 0) {
            val w = size.width
            val h = size.height
            val barW = w / n
            val off = if (shake != 0) ((shake % 3) - 1) * h * 0.04f else 0f

            drawLine(
                color = Color(0x55FFFFFF),
                start = Offset(0f, h / 2),
                end = Offset(w, h / 2),
                strokeWidth = 1f
            )

            for (i in 0 until n) {
                val x = (i + 0.5f) * w / n
                val p = peaks[i].coerceIn(0f, 1f) * (h / 2f) * 0.95f
                drawLine(
                    color = line,
                    start = Offset(x, h / 2 - p + off),
                    end = Offset(x, h / 2 + p + off),
                    strokeWidth = barW
                )
            }
        }
    }
}

@Composable
fun VMeter(
    level: Float,
    modifier: Modifier = Modifier
) {
    Box(modifier.background(C_DARK)) {
        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .fillMaxHeight(level.coerceIn(0f, 1f))
                .background(C_PINK)
        )
        Column(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .padding(2.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Text("0", color = Color(0x88FFFFFF), fontSize = 7.sp)
            Text("24", color = Color(0x88FFFFFF), fontSize = 7.sp)
            Text("54", color = Color(0x88FFFFFF), fontSize = 7.sp)
        }
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
    vels: List<List<Int>>,
    onVel: (Int, Int, Float) -> Unit,
    onResizeDelta: (Int, Int, Int) -> Unit,
    onDeleteRoll: (Int, Int) -> Unit,
    onDeleteNote: (Int, Int, Int) -> Unit,
    onMoveNote: (Int, Int, Int, Int, Int) -> Unit,
    onPasteNotes: (Int, Int, Int, List<RollNote>) -> Unit,
    onQuantize: (Int, Set<RollPoint>, Int) -> Unit,
    onTranspose: (Int, Set<RollPoint>, Int) -> Unit,
    onClearRoll: (Int) -> Unit,
    onUndo: () -> Unit,
    onRedo: () -> Unit,
    mutes: List<Boolean>,
    onMuteToggle: (Int) -> Unit,
    solos: List<Boolean>,
    onSoloToggle: (Int) -> Unit,
    midiMode: Int,
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
    levels: FloatArray,
    exportBars: Int,
    onExportBarsCycle: () -> Unit,
    exporting: Boolean,
    onExport: () -> Unit,
    selectedPad: Int,
    onSelectPad: (Int) -> Unit,
    peaks: FloatArray,
    padPeaks: List<FloatArray>,
    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    loopOn: Boolean,
    onLoopToggle: () -> Unit,
    onTrim: () -> Unit,
    onDelete: () -> Unit,
    reverse: Boolean,
    onReverseToggle: () -> Unit,
    padPitch: Float,
    onPadPitch: (Float) -> Unit,
    padVol: Float,
    onPadVol: (Float) -> Unit,
    padPan: Float,
    onPadPan: (Float) -> Unit,
    pollTick: Int,
    crunch: Boolean,
    onCrunchChange: (Boolean) -> Unit,
    stretch: Int,
    onStretch: (Int) -> Unit,
    padAttack: Float,
    onPadAttack: (Float) -> Unit,
    padRelease: Float,
    onPadRelease: (Float) -> Unit,
    padTone: Float,
    onPadTone: (Float) -> Unit,
    onTool: (String) -> Unit,
    onPreviewPad: () -> Unit,
    labels: List<String>,
    onLabel: (String) -> Unit,
    wall: ImageBitmap?,
    wallFx: Int,
    onLoadWallpaper: () -> Unit,
    onWallFx: () -> Unit,
    onClearWallpaper: () -> Unit
) {
    Box(modifier = Modifier.fillMaxSize()) {
        if (wall != null) {
            Wallpaper(bmp = wall, fx = wallFx)
        }
        Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            TabBtn("SAMPLE", view == 0) { onViewChange(0) }
            TabBtn("SEQ", view == 1) { onViewChange(1) }
            TabBtn("ROLL", view == 3) { onViewChange(3) }
            TabBtn("MIX", view == 6) { onViewChange(6) }
            TabBtn("LIB", view == 4) { onViewChange(4) }
            TabBtn("SET", view == 7) { onViewChange(7) }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            TabBtn(if (playing) "STOP" else "PLAY", playing) { onPlayToggle() }
            TabBtn(if (gateMode) "GATE" else "SHOT", gateMode) { onGateModeChange(!gateMode) }
            TabBtn(if (crunch) "12BIT" else "CLEAN", crunch) { onCrunchChange(!crunch) }
            TabBtn(if (recording) "REC*" else "REC", recording) { onRecToggle() }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            listOf("A", "B", "C", "D").forEachIndexed { i, name ->
                TabBtn(name, bank == i) { onBankChange(i) }
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
                vels = vels,
                onVel = onVel,
                playhead = playhead,
                playing = playing
            )

            3 -> RollView(
                selectedPad = selectedPad,
                onSelectPad = onSelectPad,
                loadedPads = loadedPads,
                roll = roll,
                rollLens = rollLens,
                noteLen = noteLen,
                onNoteLenCycle = onNoteLenCycle,
                onToggleRollCell = onToggleRollCell,
                onResizeDelta = onResizeDelta,
                onVel = onVel,
                onDeleteRoll = onDeleteRoll,
                onDeleteNote = onDeleteNote,
                onMoveNote = onMoveNote,
                onPasteNotes = onPasteNotes,
                onQuantize = onQuantize,
                onTranspose = onTranspose,
                onClearRoll = onClearRoll,
                onUndo = onUndo,
                onRedo = onRedo,
                onAudition = onAudition,
                vels = vels,
                playhead = playhead,
                playing = playing
            )

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
                onMasterPan = onMasterPan,
                levels = levels,
                mutes = mutes,
                onMuteToggle = onMuteToggle,
                solos = solos,
                onSoloToggle = onSoloToggle
            )

            7 -> SettingsView(
                midiMode = midiMode,
                onMidiModeChange = onMidiModeChange,
                exportBars = exportBars,
                onExportBarsCycle = onExportBarsCycle,
                exporting = exporting,
                onExport = onExport,
                wallFx = wallFx,
                onLoadWallpaper = onLoadWallpaper,
                onWallFx = onWallFx,
                onClearWallpaper = onClearWallpaper
            )

            else -> SampleView(
                selectedPad = selectedPad,
                onSelectPad = onSelectPad,
                loadedPads = loadedPads,
                peaks = peaks,
                padPeaks = padPeaks,
                flashes = flashes,
                onPadDown = onPadDown,
                onPadUp = onPadUp,
                onPadLongPress = onPadLongPress,
                gateMode = gateMode,
                onGateModeChange = onGateModeChange,
                loopStart = loopStart,
                loopEnd = loopEnd,
                onLoopStart = onLoopStart,
                onLoopEnd = onLoopEnd,
                loopOn = loopOn,
                onLoopToggle = onLoopToggle,
                reverse = reverse,
                onReverseToggle = onReverseToggle,
                padPitch = padPitch,
                onPadPitch = onPadPitch,
                padVol = padVol,
                onPadVol = onPadVol,
                padPan = padPan,
                onPadPan = onPadPan,
                onTrim = onTrim,
                onDelete = onDelete,
                pollTick = pollTick,
                bpm = bpm,
                onBpmChange = onBpmChange,
                swing = swing,
                onSwingChange = onSwingChange,
                stretch = stretch,
                onStretch = onStretch,
                padAttack = padAttack,
                onPadAttack = onPadAttack,
                padRelease = padRelease,
                onPadRelease = onPadRelease,
                padTone = padTone,
                onPadTone = onPadTone,
                onExport = onExport,
                onTool = onTool,
                onPreviewPad = onPreviewPad,
                labels = labels,
                onLabel = onLabel
            )
        }
        }
    }
}

@Composable
fun SampleView(
    selectedPad: Int,
    onSelectPad: (Int) -> Unit,
    loadedPads: Set<Int>,
    peaks: FloatArray,
    padPeaks: List<FloatArray>,
    flashes: List<Boolean>,
    onPadDown: (Int) -> Unit,
    onPadUp: (Int) -> Unit,
    onPadLongPress: (Int) -> Unit,
    gateMode: Boolean,
    onGateModeChange: (Boolean) -> Unit,
    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    loopOn: Boolean,
    onLoopToggle: () -> Unit,
    reverse: Boolean,
    onReverseToggle: () -> Unit,
    padPitch: Float,
    onPadPitch: (Float) -> Unit,
    padVol: Float,
    onPadVol: (Float) -> Unit,
    padPan: Float,
    onPadPan: (Float) -> Unit,
    onTrim: () -> Unit,
    onDelete: () -> Unit,
    pollTick: Int,
    bpm: Float,
    onBpmChange: (Float) -> Unit,
    swing: Float,
    onSwingChange: (Float) -> Unit,
    stretch: Int,
    onStretch: (Int) -> Unit,
    padAttack: Float,
    onPadAttack: (Float) -> Unit,
    padRelease: Float,
    onPadRelease: (Float) -> Unit,
    padTone: Float,
    onPadTone: (Float) -> Unit,
    onExport: () -> Unit,
    onTool: (String) -> Unit,
    onPreviewPad: () -> Unit,
    labels: List<String>,
    onLabel: (String) -> Unit
) {
    var showBpm by remember { mutableStateOf(false) }
    var page by remember { mutableStateOf(0) }
    var showStretch by remember { mutableStateOf(false) }
    var showTools by remember { mutableStateOf(false) }
    var showLabel by remember { mutableStateOf(false) }
    var algo by remember { mutableStateOf(0) }
    var stretchLen by remember { mutableStateOf(4) }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(C_CYAN)
                .padding(10.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp)
                        .background(C_PINK)
                )
                WaveEditor(
                    peaks = peaks,
                    loopStart = loopStart,
                    loopEnd = loopEnd,
                    onLoopStart = onLoopStart,
                    onLoopEnd = onLoopEnd,
                    shake = if (flashes[selectedPad]) pollTick else 0,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(110.dp)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    KBtn("<", false, { page = (page + 2) % 3 }, Modifier.size(38.dp))
                    when (page) {
                        0 -> {
                            KBtn("ONE SHOT", !gateMode, { onGateModeChange(!gateMode) }, Modifier.weight(1f).height(42.dp))
                            KBtn("REVERSE", reverse, { onReverseToggle() }, Modifier.weight(1f).height(42.dp))
                            KBtn("LOOP", loopOn, { onLoopToggle() }, Modifier.weight(1f).height(42.dp))
                        }
                        1 -> {
                            Knob("ATK", padAttack, 0f..500f, onPadAttack)
                            Knob("REL", padRelease, 0f..1000f, onPadRelease)
                            Knob("TONE", padTone, 0f..100f, onPadTone)
                        }
                        else -> {
                            KBtn("STRETCH", false, { showStretch = true }, Modifier.weight(1f).height(42.dp))
                            KBtn("TOOLS", false, { showTools = true }, Modifier.weight(1f).height(42.dp))
                        }
                    }
                    KBtn(">", false, { page = (page + 1) % 3 }, Modifier.size(38.dp))
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Knob("VOL", padVol, 0f..150f, onPadVol)
            Knob("PITCH", padPitch, -12f..12f, onPadPitch)
            Knob("PAN", padPan, 0f..100f, onPadPan)
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                KBtn("TRIM", false, onTrim, Modifier.fillMaxWidth().height(36.dp))
                KBtn("DELETE", false, onDelete, Modifier.fillMaxWidth().height(36.dp))
            }
        }

        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            for (row in 0 until 4) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    for (col in 0 until 4) {
                        val index = row * 4 + col
                val has = loadedPads.contains(index)
                val flash = flashes[index]
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .aspectRatio(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .background(
                            if (index == selectedPad) C_CYAN
                            else if (has) C_PINK.copy(alpha = 0.75f)
                            else C_PINK.copy(alpha = 0.4f)
                        )
                        .pointerInput(index) {
                            detectTapGestures(
                                onPress = {
                                    onSelectPad(index)
                                    onPadDown(index)
                                    tryAwaitRelease()
                                    onPadUp(index)
                                }
                            )
                        }
                ) {
                    if (has) {
                        Wave(
                            peaks = padPeaks[index],
                            bg = Color.Transparent,
                            line = if (index == selectedPad) Color(0xFF083A46) else Color(0x66101418),
                            shake = if (flash) pollTick else 0,
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(6.dp)
                        )
                    }
                    Text(
                        text = labels[index].ifEmpty { "${index + 1}" },
                        color = Color.White,
                        fontSize = 9.sp,
                        maxLines = 1,
                        modifier = Modifier
                            .align(Alignment.TopStart)
                            .padding(4.dp)
                    )
                }
                    }
                }
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    "BPM ${bpm.toInt()}  (2x tap)",
                    color = Color.White, fontSize = 10.sp,
                    modifier = Modifier.pointerInput(Unit) {
                        detectTapGestures(onDoubleTap = { showBpm = !showBpm })
                    }
                )
                Fader(bpm, 60f..180f, onBpmChange, Modifier.fillMaxWidth())
            }
            Column(modifier = Modifier.weight(1f)) {
                Text("SWING ${swing.toInt()}%", color = Color.White, fontSize = 10.sp)
                Fader(swing, 0f..50f, onSwingChange, Modifier.fillMaxWidth())
            }
        }

        if (showBpm) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                var txt by remember { mutableStateOf(bpm.toInt().toString()) }
                TextField(
                    value = txt,
                    onValueChange = { txt = it.filter { ch -> ch.isDigit() } },
                    singleLine = true,
                    modifier = Modifier.width(110.dp).height(48.dp)
                )
                KBtn("SET", false, {
                    val v = txt.toFloatOrNull()
                    if (v != null) onBpmChange(v.coerceIn(60f, 180f))
                    showBpm = false
                }, Modifier.width(70.dp).height(40.dp))
            }
        }

        if (showStretch) {
            Dialog(onDismissRequest = { showStretch = false }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF3A1220))
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("TIMESTRETCH", color = Color.White, fontWeight = FontWeight.Bold)
                    KBtn(
                        "duration: " + when (stretchLen) {
                            4 -> "1 BEAT"
                            8 -> "2 BEAT"
                            16 -> "1 BAR"
                            32 -> "2 BAR"
                            64 -> "4 BAR"
                            else -> "OFF"
                        },
                        false,
                        {
                            stretchLen = when (stretchLen) {
                                4 -> 8
                                8 -> 16
                                16 -> 32
                                32 -> 64
                                else -> 4
                            }
                        },
                        Modifier.fillMaxWidth().height(44.dp)
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        listOf("MODERN", "RETRO", "BEATS", "REPITCH", "CYCLIC").forEachIndexed { i, s ->
                            KBtn(s, algo == i, { algo = i }, Modifier.weight(1f).height(36.dp))
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        KBtn("PREVIEW", false, { onPreviewPad() }, Modifier.weight(1f).height(42.dp))
                        KBtn("OK", false, { onStretch(stretchLen); showStretch = false }, Modifier.weight(1f).height(42.dp))
                    }
                }
            }
        }

        if (showLabel) {
            Dialog(onDismissRequest = { showLabel = false }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF3A1220))
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("LABEL", color = Color.White, fontWeight = FontWeight.Bold)
                    var txt by remember { mutableStateOf(labels[selectedPad]) }
                    TextField(
                        value = txt,
                        onValueChange = { txt = it },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    KBtn("OK", false, {
                        onLabel(txt)
                        showLabel = false
                    }, Modifier.fillMaxWidth().height(42.dp))
                }
            }
        }

        if (showTools) {
            Dialog(onDismissRequest = { showTools = false }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF3A1220))
                        .padding(8.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    listOf(
                        "LABEL", "CROP", "NORMALIZE", "TRIM SILENCE", "AUTO-CHOP",
                        "SPLIT STEMS", "MAKE MONO", "BOUNCE", "EXPORT"
                    ).forEach { item ->
                        KBtn(item, false, {
                            showTools = false
                            when (item) {
                                "CROP" -> onTrim()
                                "EXPORT" -> onExport()
                                "LABEL" -> showLabel = true
                                else -> onTool(item)
                            }
                        }, Modifier.fillMaxWidth().height(40.dp))
                    }
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
    onMasterPan: (Float) -> Unit,
    levels: FloatArray,
    mutes: List<Boolean>,
    onMuteToggle: (Int) -> Unit,
    solos: List<Boolean>,
    onSoloToggle: (Int) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        for (ch in 0 until 5) {
            val pad = mixAssign[ch]
            val lvl = if (levels.size > pad) levels[pad] else 0f
            Column(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .background(C_DARK)
                    .padding(6.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(30.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0xFF3A2F55)),
                    contentAlignment = Alignment.Center
                ) {
                    Text("BUS ${'A' + ch}", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                }
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(24.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(C_DARK)
                        .clickable { onMixAssignCycle(ch) },
                    contentAlignment = Alignment.Center
                ) {
                    Text("P${pad + 1}", color = C_CYAN, fontSize = 10.sp)
                }
                VMeter(level = lvl, modifier = Modifier.fillMaxWidth().height(200.dp))
                Fader(value = volOf(pad), range = 0f..150f, onValueChange = { onVol(pad, it) }, modifier = Modifier.fillMaxWidth())
                Fader(value = panOf(pad), range = 0f..100f, onValueChange = { onPan(pad, it) }, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    Box(
                        modifier = Modifier.weight(1f).height(30.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(if (mutes[pad]) C_PINK else Color(0xFF3A2F55))
                            .clickable { onMuteToggle(pad) },
                        contentAlignment = Alignment.Center
                    ) { Text("M", color = Color.White, fontSize = 10.sp) }
                    Box(
                        modifier = Modifier.weight(1f).height(30.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(if (solos[pad]) C_CYAN else Color(0xFF3A2F55))
                            .clickable { onSoloToggle(pad) },
                        contentAlignment = Alignment.Center
                    ) { Text("S", color = Color(0xFF06201D), fontSize = 10.sp) }
                }
            }
        }
        Column(
            modifier = Modifier
                .weight(1f)
                .clip(RoundedCornerShape(10.dp))
                .background(C_DARK)
                .padding(6.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Box(
                modifier = Modifier.fillMaxWidth().height(30.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(Color(0xFF3A2F55)),
                contentAlignment = Alignment.Center
            ) { Text("MAIN", color = C_PINK, fontWeight = FontWeight.Bold, fontSize = 10.sp) }
            val ml = if (levels.size > 16) levels[16] else 0f
            val mrv = if (levels.size > 17) levels[17] else 0f
            VMeter(level = if (ml > mrv) ml else mrv, modifier = Modifier.fillMaxWidth().height(200.dp))
            Fader(value = masterVol, range = 0f..150f, onValueChange = onMasterVol, modifier = Modifier.fillMaxWidth())
            Fader(value = masterPan, range = 0f..100f, onValueChange = onMasterPan, modifier = Modifier.fillMaxWidth())
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
    vels: List<List<Int>>,
    onVel: (Int, Int, Float) -> Unit,
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
                    modifier = Modifier.width(22.dp).height(24.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (mutes[pad]) C_PINK else C_DARK)
                        .clickable { onMuteToggle(pad) },
                    contentAlignment = Alignment.Center
                ) { Text("M", color = Color.White, fontSize = 8.sp) }
                Box(
                    modifier = Modifier.width(22.dp).height(24.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(if (solos[pad]) C_CYAN else C_DARK)
                        .clickable { onSoloToggle(pad) },
                    contentAlignment = Alignment.Center
                ) { Text("S", color = Color(0xFF06201D), fontSize = 8.sp) }
                for (step in 0 until 16) {
                    val on = (pattern[pad] ushr step) and 1 == 1
                    val vel = vels[pad][step]
                    val offColor = when {
                        playing && step == playhead -> Color(0xFF3A2F55)
                        step % 4 == 0 -> Color(0xFF2E2447)
                        else -> C_DARK
                    }
                    Box(
                        modifier = Modifier.weight(1f).height(24.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(
                                if (on) C_PINK.copy(alpha = (0.3f + 0.7f * vel / 150f)) else offColor
                            )
                            .pointerInput(on) {
                                detectTapGestures(onTap = { onToggleStep(pad, step) })
                            }
                            .pointerInput(on) {
                                if (on) {
                                    detectDragGestures { change, drag ->
                                        change.consume()
                                        onVel(pad, step, -drag.y / 2f)
                                    }
                                }
                            }
                    )
                }
            }
        }
    }
}

fun fmtSteps(u: Int): String {
    val st = u / 4f
    return if (st == st.toInt().toFloat()) "${st.toInt()}" else "$st"
}

fun rollNoteStart(row: List<Int>, rowLen: List<Int>, step: Int, pitch: Int): Int {
    if (step !in 0 until ROLL_STEPS || pitch !in 0 until ROLL_PITCHES) return -1
    if ((row[step] and (1 shl pitch)) != 0) return step
    for (candidate in 0 until step) {
        if ((row[candidate] and (1 shl pitch)) != 0) {
            val cells = (rowLen[candidate] + 3) / 4
            if (step < candidate + cells) return candidate
        }
    }
    return -1
}

private fun pitchName(pitch: Int): String {
    val midi = 48 + pitch
    val names = listOf("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return "${names[midi % 12]}${midi / 12 - 1}"
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
    onResizeDelta: (Int, Int, Int) -> Unit,
    onVel: (Int, Int, Float) -> Unit,
    onDeleteRoll: (Int, Int) -> Unit,
    onDeleteNote: (Int, Int, Int) -> Unit,
    onMoveNote: (Int, Int, Int, Int, Int) -> Unit,
    onPasteNotes: (Int, Int, Int, List<RollNote>) -> Unit,
    onQuantize: (Int, Set<RollPoint>, Int) -> Unit,
    onTranspose: (Int, Set<RollPoint>, Int) -> Unit,
    onClearRoll: (Int) -> Unit,
    onUndo: () -> Unit,
    onRedo: () -> Unit,
    onAudition: (Int, Int) -> Unit,
    vels: List<List<Int>>,
    playhead: Int,
    playing: Boolean
) {
    var tool by remember { mutableStateOf(RollTool.DRAW) }
    var zoom by remember { mutableStateOf(1f) }
    var snap by remember { mutableStateOf(1) }
    var selectedNotes by remember { mutableStateOf(setOf<RollPoint>()) }
    var clipboard by remember { mutableStateOf(emptyList<RollNote>()) }
    val scrollX = rememberScrollState()
    val scrollY = rememberScrollState()

    val currentRow = roll[selectedPad]
    val currentLens = rollLens[selectedPad]
    val currentVels = vels[selectedPad]
    val noteColor = C_PINK
    val noteCount = currentRow.sumOf { Integer.bitCount(it) }

    Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            for (pad in 0 until 16) {
                val bg = when {
                    pad == selectedPad -> C_CYAN
                    loadedPads.contains(pad) -> C_PINK.copy(alpha = 0.75f)
                    else -> C_DARK
                }
                Box(
                    modifier = Modifier.weight(1f).height(27.dp).clip(RoundedCornerShape(6.dp)).background(bg).clickable {
                        onSelectPad(pad)
                        selectedNotes = emptySet()
                    },
                    contentAlignment = Alignment.Center
                ) { Text("${pad + 1}", color = Color.White, fontSize = 8.sp) }
            }
        }

        Row(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            KBtn("DRAW", tool == RollTool.DRAW, { tool = RollTool.DRAW }, Modifier.width(58.dp).height(30.dp))
            KBtn("SELECT", tool == RollTool.SELECT, { tool = RollTool.SELECT }, Modifier.width(64.dp).height(30.dp))
            KBtn("ERASE", tool == RollTool.ERASE, { tool = RollTool.ERASE }, Modifier.width(58.dp).height(30.dp))
            KBtn("VEL", tool == RollTool.VELOCITY, { tool = RollTool.VELOCITY }, Modifier.width(48.dp).height(30.dp))
            KBtn("RESIZE", tool == RollTool.RESIZE, { tool = RollTool.RESIZE }, Modifier.width(62.dp).height(30.dp))
            KBtn("LEN $noteLen", false, onNoteLenCycle, Modifier.width(62.dp).height(30.dp))
            KBtn("SNAP ${snap * 4}", false, { snap = if (snap == 1) 2 else if (snap == 2) 4 else 1 }, Modifier.width(72.dp).height(30.dp))
            KBtn("−", false, { zoom = (zoom - 0.25f).coerceAtLeast(0.75f) }, Modifier.width(34.dp).height(30.dp))
            KBtn("${(zoom * 100).toInt()}%", false, { zoom = 1f }, Modifier.width(58.dp).height(30.dp))
            KBtn("+", false, { zoom = (zoom + 0.25f).coerceAtMost(2.5f) }, Modifier.width(34.dp).height(30.dp))
        }
        Row(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            KBtn("UNDO", false, onUndo, Modifier.width(56.dp).height(28.dp))
            KBtn("REDO", false, onRedo, Modifier.width(56.dp).height(28.dp))
            KBtn("COPY", false, {
                val points = if (selectedNotes.isEmpty()) {
                    (0 until ROLL_STEPS).flatMap { st -> (0 until ROLL_PITCHES).filter { pi -> (currentRow[st] and (1 shl pi)) != 0 }.map { pi -> RollPoint(st, pi) } }
                } else selectedNotes.toList()
                val notes = points.mapNotNull { point ->
                    if (point.step !in 0 until ROLL_STEPS || (currentRow[point.step] and (1 shl point.pitch)) == 0) null
                    else RollNote(point.step, point.pitch, currentLens[point.step], currentVels[point.step])
                }
                if (notes.isNotEmpty()) {
                    val baseStep = notes.minOf { it.step }
                    val basePitch = notes.minOf { it.pitch }
                    clipboard = notes.map { it.copy(step = it.step - baseStep, pitch = it.pitch - basePitch) }
                }
            }, Modifier.width(58.dp).height(28.dp))
            KBtn("PASTE", clipboard.isNotEmpty(), {
                val anchor = selectedNotes.minWithOrNull(compareBy<RollPoint> { it.step }.thenBy { it.pitch }) ?: RollPoint(0, 0)
                onPasteNotes(selectedPad, anchor.step, anchor.pitch, clipboard)
            }, Modifier.width(58.dp).height(28.dp))
            KBtn("DEL", false, {
                if (selectedNotes.isEmpty()) onClearRoll(selectedPad)
                else {
                    selectedNotes.forEach { point -> onDeleteNote(selectedPad, point.step, point.pitch) }
                    selectedNotes = emptySet()
                }
            }, Modifier.width(48.dp).height(28.dp))
            KBtn("QUANT", false, { onQuantize(selectedPad, selectedNotes, snap) }, Modifier.width(60.dp).height(28.dp))
            KBtn("−12", false, { onTranspose(selectedPad, selectedNotes, -1) }, Modifier.width(48.dp).height(28.dp))
            KBtn("+12", false, { onTranspose(selectedPad, selectedNotes, 1) }, Modifier.width(48.dp).height(28.dp))
            Text("$noteCount notes", color = Color(0xFF9BB7C4), fontSize = 10.sp, modifier = Modifier.padding(horizontal = 6.dp, vertical = 8.dp))
        }

        Text(
            "${tool.name}  •  Tap adds/removes  •  Select then drag to move  •  Drag note edge to resize  •  Drag vertically for velocity",
            color = Color(0xFF9BB7C4), fontSize = 9.sp, maxLines = 1
        )

        BoxWithConstraints(modifier = Modifier.fillMaxSize().weight(1f)) {
            val keyWidth = 46.dp
            val timelineWidth = maxOf(900.dp, maxWidth - keyWidth) * zoom
            Row(modifier = Modifier.fillMaxSize().verticalScroll(scrollY)) {
                Column(modifier = Modifier.width(keyWidth)) {
                    Box(modifier = Modifier.fillMaxWidth().height(22.dp), contentAlignment = Alignment.Center) {
                        Text("KEY", color = Color(0xFF9BB7C4), fontSize = 8.sp)
                    }
                    for (pitch in (ROLL_PITCHES - 1) downTo 0) {
                        val black = pitchName(pitch).contains("#")
                        Box(
                            modifier = Modifier.fillMaxWidth().height(25.dp).clip(RoundedCornerShape(2.dp)).background(if (black) Color(0xFF171021) else Color(0xFFE8F4F8)).clickable { onAudition(selectedPad, pitch - 12) },
                            contentAlignment = Alignment.Center
                        ) { Text(pitchName(pitch), color = if (black) Color.White else Color.Black, fontSize = 7.sp) }
                    }
                }

                Column(modifier = Modifier.weight(1f).horizontalScroll(scrollX)) {
                    Canvas(modifier = Modifier.width(timelineWidth).fillMaxWidth().height(22.dp)) {
                        val cellW = size.width / ROLL_STEPS
                        for (step in 0 until ROLL_STEPS) {
                            val strong = step % 16 == 0
                            drawRect(if (strong) Color(0xFF314452) else Color(0xFF1E2B34), Offset(step * cellW, 0f), Size(cellW - 1f, size.height))
                            if (step % 4 == 0) drawLine(Color(0xFF9BB7C4), Offset(step * cellW + 2f, 4f), Offset(step * cellW + 2f, size.height - 4f), 1f)
                        }
                        drawIntoCanvas { canvas ->
                            val paint = android.graphics.Paint().apply { color = android.graphics.Color.LTGRAY; textSize = 10f }
                            for (step in 0 until ROLL_STEPS step 4) {
                                canvas.nativeCanvas.drawText("${step / 4 + 1}", step * cellW + 4f, 15f, paint)
                            }
                        }
                    }
                    for (pitch in (ROLL_PITCHES - 1) downTo 0) {
                        val rowIndex = ROLL_PITCHES - 1 - pitch
                        val black = pitchName(pitch).contains("#")
                        Canvas(
                            modifier = Modifier.width(timelineWidth).height(25.dp).pointerInput(currentRow, currentLens, tool, snap) {
                                detectTapGestures(
                                    onTap = { pos ->
                                        val cellW = size.width / ROLL_STEPS
                                        val rawStep = (pos.x / cellW).toInt().coerceIn(0, ROLL_STEPS - 1)
                                        val step = ((rawStep + snap / 2) / snap * snap).coerceIn(0, ROLL_STEPS - 1)
                                        val start = rollNoteStart(currentRow, currentLens, rawStep, pitch)
                                        when (tool) {
                                            RollTool.DRAW -> onToggleRollCell(selectedPad, if (start >= 0) start else step, pitch)
                                            RollTool.ERASE -> if (start >= 0) onDeleteNote(selectedPad, start, pitch)
                                            RollTool.SELECT, RollTool.VELOCITY, RollTool.RESIZE -> if (start >= 0) selectedNotes = if (selectedNotes.contains(RollPoint(start, pitch))) selectedNotes - RollPoint(start, pitch) else selectedNotes + RollPoint(start, pitch)
                                        }
                                    },
                                    onLongPress = { pos ->
                                        val cellW = size.width / ROLL_STEPS
                                        val step = (pos.x / cellW).toInt().coerceIn(0, ROLL_STEPS - 1)
                                        val start = rollNoteStart(currentRow, currentLens, step, pitch)
                                        if (start >= 0) onDeleteNote(selectedPad, start, pitch)
                                    }
                                )
                            }.pointerInput(currentRow, currentLens, tool, snap) {
                                var from: RollPoint? = null
                                var lastStep = -1
                                detectDragGestures(
                                    onDragStart = { pos ->
                                        val cellW = size.width / ROLL_STEPS
                                        val step = (pos.x / cellW).toInt().coerceIn(0, ROLL_STEPS - 1)
                                        val start = rollNoteStart(currentRow, currentLens, step, pitch)
                                        from = if (start >= 0) RollPoint(start, pitch) else null
                                        lastStep = step
                                    },
                                    onDragEnd = { from = null },
                                    onDragCancel = { from = null },
                                    onDrag = { change, drag ->
                                        change.consume()
                                        val cellW = size.width / ROLL_STEPS
                                        val step = (change.position.x / cellW).toInt().coerceIn(0, ROLL_STEPS - 1)
                                        val source = from
                                        if (source != null && step != lastStep) {
                                            when (tool) {
                                                RollTool.SELECT -> {
                                                    val delta = step - source.step
                                                    val pitchDelta = ((-drag.y / 25f).toInt()).coerceIn(-ROLL_PITCHES, ROLL_PITCHES)
                                                    val destination = (source.pitch + pitchDelta).coerceIn(0, ROLL_PITCHES - 1)
                                                    val snappedStep = (source.step + delta).coerceIn(0, ROLL_STEPS - 1)
                                                    onMoveNote(selectedPad, source.step, source.pitch, snappedStep, destination)
                                                    selectedNotes = setOf(RollPoint(snappedStep, destination))
                                                    from = RollPoint(snappedStep, destination)
                                                }
                                                RollTool.RESIZE -> onResizeDelta(selectedPad, source.step, ((drag.x / cellW) * 4f).toInt())
                                                RollTool.VELOCITY -> onVel(selectedPad, source.step, -drag.y / 2f)
                                                else -> Unit
                                            }
                                            lastStep = step
                                        } else if (source != null) {
                                            when (tool) {
                                                RollTool.RESIZE -> onResizeDelta(selectedPad, source.step, ((drag.x / cellW) * 4f).toInt())
                                                RollTool.VELOCITY -> onVel(selectedPad, source.step, -drag.y / 2f)
                                                else -> Unit
                                            }
                                        }
                                    }
                                )
                            }
                        ) {
                            val cellW = size.width / ROLL_STEPS
                            for (step in 0 until ROLL_STEPS) {
                                val grid = when {
                                    playing && step == playhead -> Color(0x66FFFFFF)
                                    step % 16 == 0 -> Color(0xFF293944)
                                    step % 4 == 0 -> Color(0xFF23313A)
                                    black -> Color(0xFF171F26)
                                    else -> Color(0xFF1B252D)
                                }
                                drawRect(grid, Offset(step * cellW + 0.5f, 0f), Size(cellW - 1f, size.height))
                            }
                            for (step in 0 until ROLL_STEPS) {
                                if ((currentRow[step] and (1 shl pitch)) != 0) {
                                    val len = currentLens[step].coerceAtLeast(1) / 4f
                                    val x0 = step * cellW
                                    val x1 = (step + len).coerceAtMost(ROLL_STEPS.toFloat()) * cellW
                                    val selected = selectedNotes.contains(RollPoint(step, pitch))
                                    val alpha = (0.25f + 0.75f * currentVels[step] / 150f).coerceIn(0.25f, 1f)
                                    drawRoundRect(color = if (selected) Color(0xFFFBBF24) else noteColor.copy(alpha = alpha), topLeft = Offset(x0 + 1f, 2f), size = Size((x1 - x0 - 2f).coerceAtLeast(3f), size.height - 4f), cornerRadius = CornerRadius(4f))
                                    drawRect(Color.White, Offset(x0 + 1f, 2f), Size(2f, size.height - 4f))
                                    if (x1 - x0 > 20f) drawRect(Color(0xAAFFFFFF), Offset(x1 - 3f, 2f), Size(2f, size.height - 4f))
                                }
                            }
                        }
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
                    armedFile != null -> Color(0xFF3A2F55)
                    pad == selectedPad -> C_CYAN
                    loadedPads.contains(pad) -> C_PINK.copy(alpha = 0.75f)
                    else -> C_DARK
                }
                Box(
                    modifier = Modifier.weight(1f).height(30.dp)
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
                    Text("${pad + 1}", color = Color.White, fontSize = 8.sp)
                }
            }
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            KBtn("IMPORT", false, onImport, Modifier.width(90.dp).height(36.dp))
            Text(
                if (armedFile != null) "Holding: $armedFile — tap a pad"
                else "Tap = play. Hold = pick up, then tap pad",
                color = if (armedFile != null) C_CYAN else Color(0xFF9BB7C4),
                fontSize = 9.sp, maxLines = 1
            )
        }
        LazyColumn(
            modifier = Modifier.fillMaxSize().weight(1f),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            items(files.size) { i ->
                val name = files[i]
                Box(
                    modifier = Modifier.fillMaxWidth().height(42.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(if (armedFile == name) C_PINK else C_DARK)
                        .pointerInput(name) {
                            detectTapGestures(
                                onTap = {
                                    if (armedFile == name) armedFile = null
                                    else onPreview(name)
                                },
                                onLongPress = { armedFile = name }
                            )
                        },
                    contentAlignment = Alignment.CenterStart
                ) {
                    Text(
                        name,
                        color = if (armedFile == name) Color.White else Color(0xFFD7E6EE),
                        fontSize = 10.sp,
                        modifier = Modifier.padding(horizontal = 12.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun SettingsView(
    midiMode: Int,
    onMidiModeChange: () -> Unit,
    exportBars: Int,
    onExportBarsCycle: () -> Unit,
    exporting: Boolean,
    onExport: () -> Unit,
    wallFx: Int,
    onLoadWallpaper: () -> Unit,
    onWallFx: () -> Unit,
    onClearWallpaper: () -> Unit
) {
    var colorEl by remember { mutableStateOf(-1) }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("SETTINGS", color = C_CYAN, fontWeight = FontWeight.Bold)

        Text("COLORS", color = C_CYAN, fontWeight = FontWeight.Bold)
        listOf("BACKGROUND", "ACCENT", "PINK", "WAVE BG", "PANELS").forEachIndexed { i, name ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(name, color = Color.White, fontSize = 11.sp, modifier = Modifier.weight(1f))
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(themeGet(i))
                        .clickable { colorEl = i }
                )
            }
        }

        Text("WALLPAPER", color = C_CYAN, fontWeight = FontWeight.Bold)
        KBtn("LOAD WALLPAPER", false, onLoadWallpaper, Modifier.fillMaxWidth().height(44.dp))
        KBtn(
            "FX: " + when (wallFx) { 0 -> "OFF"; 1 -> "ZOOM"; 2 -> "PAN"; else -> "PULSE" },
            wallFx != 0, onWallFx, Modifier.fillMaxWidth().height(44.dp)
        )
        KBtn("CLEAR WALLPAPER", false, onClearWallpaper, Modifier.fillMaxWidth().height(44.dp))
        KBtn(
            when (midiMode) {
                1 -> "MIDI: MASTER"
                2 -> "MIDI: SLAVE"
                else -> "MIDI: OFF"
            },
            midiMode != 0,
            onMidiModeChange,
            Modifier.fillMaxWidth().height(44.dp)
        )
        KBtn("EXPORT LENGTH: x$exportBars", false, onExportBarsCycle, Modifier.fillMaxWidth().height(44.dp))
        KBtn(if (exporting) "EXPORTING..." else "EXPORT BEAT", exporting, onExport, Modifier.fillMaxWidth().height(44.dp))

        if (colorEl >= 0) {
            Dialog(onDismissRequest = { colorEl = -1 }) {
                Column(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0xFF201018))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("COLOR", color = Color.White, fontWeight = FontWeight.Bold)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        PALETTE.take(8).forEach { c ->
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .height(40.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(c)
                                    .clickable {
                                        themeSet(colorEl, c)
                                        colorEl = -1
                                    }
                            )
                        }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        PALETTE.drop(8).forEach { c ->
                            Box(
                                modifier = Modifier
                                    .weight(1f)
                                    .height(40.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(c)
                                    .clickable {
                                        themeSet(colorEl, c)
                                        colorEl = -1
                                    }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun Wallpaper(bmp: ImageBitmap, fx: Int) {
    val inf = rememberInfiniteTransition()
    val t by inf.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(6000), RepeatMode.Reverse)
    )
    val scale = when (fx) { 1 -> 1f + 0.15f * t; else -> 1f }
    val alpha = when (fx) { 3 -> 0.4f + 0.3f * t; else -> 0.7f }
    val offX = when (fx) { 2 -> (t - 0.5f) * 0.1f; else -> 0f }

    Canvas(modifier = Modifier.fillMaxSize()) {
        val w = size.width
        val h = size.height
        val bw = bmp.width.toFloat()
        val bh = bmp.height.toFloat()
        if (bw > 0f && bh > 0f) {
            val base = maxOf(w / bw, h / bh)
            val s = base * scale
            val dw = bw * s
            val dh = bh * s
            val dx = (w - dw) / 2 + offX * w
            val dy = (h - dh) / 2
            drawImage(
                image = bmp,
                dstOffset = IntOffset(dx.toInt(), dy.toInt()),
                dstSize = IntSize(dw.toInt(), dh.toInt()),
                alpha = alpha
            )
        }
    }
}

@Composable
fun WaveEditor(
    peaks: FloatArray,
    loopStart: Float,
    loopEnd: Float,
    onLoopStart: (Float) -> Unit,
    onLoopEnd: (Float) -> Unit,
    shake: Int,
    modifier: Modifier = Modifier
) {
    var zoom by remember { mutableStateOf(1f) }
    var center by remember { mutableStateOf(0.5f) }
    val viewW = 1f / zoom
    var viewStart = center - viewW / 2f
    if (viewStart < 0f) viewStart = 0f
    if (viewStart > 1f - viewW) viewStart = 1f - viewW

    val zoomRef = rememberUpdatedState(zoom)
    val centerRef = rememberUpdatedState(center)
    val vsRef = rememberUpdatedState(viewStart)
    val lsRef = rememberUpdatedState(loopStart)
    val leRef = rememberUpdatedState(loopEnd)
    val lineColor = C_CYAN
    val regionColor = C_PINK

    BoxWithConstraints(modifier = modifier) {
        val w = constraints.maxWidth.toFloat()
        Canvas(
            modifier = Modifier
                .fillMaxSize()
                .background(C_WAVEBG)
                .pointerInput(Unit) {
                    detectTransformGestures { centroid, pan, zoomChange, _ ->
                        val oldZ = zoomRef.value
                        val z = (oldZ * zoomChange).coerceIn(1f, 64f)
                        val oldVw = 1f / oldZ
                        val newVw = 1f / z
                        val cx = centroid.x / w
                        val lsX = (lsRef.value / 100f - vsRef.value) / oldVw
                        val leX = (leRef.value / 100f - vsRef.value) / oldVw
                        val edge = 30f / w
                        when {
                            zoomChange != 1f -> {
                                val anchor = vsRef.value + cx * oldVw
                                val ns = anchor - cx * newVw - (pan.x / w) * newVw
                                zoom = z
                                center = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                            }
                            kotlin.math.abs(cx - lsX) < edge -> {
                                onLoopStart(lsRef.value + pan.x / w * oldVw * 100f)
                            }
                            kotlin.math.abs(cx - leX) < edge -> {
                                onLoopEnd(leRef.value + pan.x / w * oldVw * 100f)
                            }
                            cx > lsX && cx < leX -> {
                                val d = pan.x / w * oldVw * 100f
                                onLoopStart(lsRef.value + d)
                                onLoopEnd(leRef.value + d)
                            }
                            else -> {
                                val anchor = vsRef.value + cx * oldVw
                                val ns = anchor - cx * newVw - (pan.x / w) * newVw
                                center = (ns + newVw / 2f).coerceIn(newVw / 2f, 1f - newVw / 2f)
                            }
                        }
                    }
                }
        ) {
            val n = peaks.size
            val h = size.height
            val width = size.width
            if (n > 0) {
                val ls = ((loopStart / 100f - viewStart) / viewW).coerceIn(0f, 1f) * width
                val le = ((loopEnd / 100f - viewStart) / viewW).coerceIn(0f, 1f) * width
                drawRoundRect(
                    color = regionColor.copy(alpha = 0.35f),
                    topLeft = Offset(ls, 0f),
                    size = Size(le - ls, h),
                    cornerRadius = CornerRadius(10f)
                )
                drawRect(color = regionColor, topLeft = Offset(ls, 0f), size = Size(le - ls, 6f))
                drawRect(color = regionColor, topLeft = Offset(ls, 0f), size = Size(5f, h))
                drawRect(color = regionColor, topLeft = Offset(le - 5f, 0f), size = Size(5f, h))
                drawLine(Color(0x55FFFFFF), Offset(0f, h / 2), Offset(width, h / 2), 1f)
                val off = if (shake != 0) ((shake % 3) - 1) * h * 0.04f else 0f
                val bars = 160
                for (bIdx in 0 until bars) {
                    val fa = viewStart + viewW * bIdx / bars
                    val fb = viewStart + viewW * (bIdx + 1) / bars
                    var ia = (fa * n).toInt()
                    var ib = (fb * n).toInt()
                    if (ib <= ia) ib = ia + 1
                    if (ia < 0) ia = 0
                    if (ib > n) ib = n
                    var m = 0f
                    val stride = 1 + (ib - ia) / 32
                    var i = ia
                    while (i < ib) {
                        val a = kotlin.math.abs(peaks[i])
                        if (a > m) m = a
                        i += stride
                    }
                    val x = (bIdx + 0.5f) * width / bars
                    val p = m.coerceIn(0f, 1f) * (h / 2f) * 0.95f
                    drawLine(lineColor, Offset(x, h / 2 - p + off), Offset(x, h / 2 + p + off), width / bars)
                }
            }
        }
        Text(
            "x${zoom.toInt()}",
            color = Color.White,
            fontSize = 9.sp,
            modifier = Modifier.align(Alignment.TopEnd).padding(4.dp)
        )
    }
}

fun dySafe(y: Float): Float = y / 2f
