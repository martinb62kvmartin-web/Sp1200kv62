package com.example.sp1200

import android.content.pm.PackageManager
import android.media.midi.MidiDevice
import android.media.midi.MidiDeviceInfo
import android.media.midi.MidiManager
import android.media.midi.MidiReceiver
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
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
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
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
    private external fun nativeSeqSetPlaying(playing: Boolean)
    private external fun nativeSeqSetBpm(bpm: Float)
    private external fun nativeSeqSetSwing(swing: Float)
    private external fun nativeSeqSetMask(padIndex: Int, mask: Int)
    private external fun nativeSetRoll(padIndex: Int, step: Int, value: Int)
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

    private lateinit var midiManager: MidiManager
    private var midiDevice: MidiDevice? = null
    private var sendFn: ((ByteArray) -> Unit)? = null
    private var closePortsFn: (() -> Unit)? = null

    @Volatile
    private var clockRunning = false
    private var clockThread: Thread? = null
    private var lastTicks = 0L

    private val pollHandler = Handler(Looper.getMainLooper())
    private var prevHits = MutableList(8) { 0L }

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
    private var patternBanks by mutableStateOf(List(4) { List(8) { 0 } })
    private var rollBanks by mutableStateOf(List(4) { List(8) { List(16) { 0 } } })
    private var mutes by mutableStateOf(List(8) { false })
    private var solos by mutableStateOf(List(8) { false })
    private var midiMode by mutableStateOf(0)
    private var midiDeviceName by mutableStateOf("none")
    private var recording by mutableStateOf(false)
    private var playhead by mutableStateOf(0)
    private var pollTick by mutableStateOf(0)
    private var hitTimes by mutableStateOf(List(8) { 0L })

    private var selectedPad by mutableStateOf(0)
    private var peaks by mutableStateOf(FloatArray(0))
    private var loopStartBanks by mutableStateOf(List(4) { List(8) { 0f } })
    private var loopEndBanks by mutableStateOf(List(4) { List(8) { 100f } })
    private var loopOnBanks by mutableStateOf(List(4) { List(8) { false } })

    private var pitchBanks by mutableStateOf(List(4) { List(8) { 0f } })
    private var attackBanks by mutableStateOf(List(4) { List(8) { 0f } })
    private var decayBanks by mutableStateOf(List(4) { List(8) { 0f } })
    private var sustainBanks by mutableStateOf(List(4) { List(8) { 100f } })
    private var releaseBanks by mutableStateOf(List(4) { List(8) { 50f } })

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

            val banksArr = JSONArray()
            for (b in 0 until 4) {
                val bo = JSONObject()
                bo.put("patterns", JSONArray(patternBanks[b]))

                val rollArr = JSONArray()
                for (p in 0 until 8) {
                    rollArr.put(JSONArray(rollBanks[b][p]))
                }
                bo.put("roll", rollArr)

                val loopsArr = JSONArray()
                for (p in 0 until 8) {
                    val lo = JSONObject()
                    lo.put("s", loopStartBanks[b][p])
                    lo.put("e", loopEndBanks[b][p])
                    lo.put("on", loopOnBanks[b][p])
                    loopsArr.put(lo)
                }
                bo.put("loops", loopsArr)

                val paramsArr = JSONArray()
                for (p in 0 until 8) {
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
                mutes = (0 until 8).map { m.optBoolean(it, false) }
            }
            root.optJSONArray("solos")?.let { s ->
                solos = (0 until 8).map { s.optBoolean(it, false) }
            }

            val banksArr = root.optJSONArray("banks") ?: return

            val newPatterns = patternBanks.toMutableList()
            val newRolls = rollBanks.toMutableList()
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
                    newPatterns[b] = (0 until 8).map { pat.optInt(it, 0) }
                }

                bo.optJSONArray("roll")?.let { ra ->
                    val rows = rollBanks[b].toMutableList()
                    for (p in 0 until minOf(8, ra.length())) {
                        val st = ra.optJSONArray(p) ?: continue
                        rows[p] = (0 until 16).map { st.optInt(it, 0) }
                    }
                    newRolls[b] = rows
                }

                bo.optJSONArray("loops")?.let { la ->
                    for (p in 0 until minOf(8, la.length())) {
                        val lo = la.optJSONObject(p) ?: continue
                        newLS[b] = newLS[b].toMutableList().also { it[p] = lo.optDouble("s", 0.0).toFloat() }
                        newLE[b] = newLE[b].toMutableList().also { it[p] = lo.optDouble("e", 100.0).toFloat() }
                        newLO[b] = newLO[b].toMutableList().also { it[p] = lo.optBoolean("on", false) }
                    }
                }

                bo.optJSONArray("params")?.let { pa ->
                    for (p in 0 until minOf(8, pa.length())) {
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

        for (p in 0 until 8) {
            nativeSetMute(p, mutes[p])
            nativeSetSolo(p, solos[p])
        }

        for (b in 0 until 4) {
            nativeSetBank(b)
            for (p in 0 until 8) {
                nativeSeqSetMask(p, patternBanks[b][p])
                for (st in 0 until 16) {
                    val v = rollBanks[b][p][st]
                    if (v != 0) nativeSetRoll(p, st, v)
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
            for (p in 0 until 8) {
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

        midiManager = getSystemService(MIDI_SERVICE) as MidiManager

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF141428)
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
                        onToggleRollCell = { pad, step, value ->
                            rollBanks = rollBanks.toMutableList().also { outer ->
                                outer[bank] = outer[bank].toMutableList().also { mid ->
                                    mid[pad] = mid[pad].toMutableList().also { it[step] = value }
                                }
                            }
                            nativeSetRoll(pad, step, value)
                        },
                        playhead = playhead,
                        flashes = hitTimes.map { System.currentTimeMillis() - it < 150 },
                        recording = recording,
                        onRecToggle = { onRecToggle() },
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
                for (i in 0 until 8) {
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
    0 -> Color(0xFFE53935)
    1 -> Color(0xFFFB8C00)
    2 -> Color(0xFFFDD835)
    3 -> Color(0xFF43A047)
    4 -> Color(0xFF1E88E5)
    5 -> Color(0xFF8E24AA)
    6 -> Color(0xFF00ACC1)
    else -> Color(0xFF546E7A)
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
            containerColor = if (active) Color(0xFFE91E5A) else Color(0xFF262636)
        ),
        contentPadding = PaddingValues(horizontal = 2.dp, vertical = 2.dp)
    ) {
        Text(
            text = label,
            color = Color.White,
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
    onToggleRollCell: (Int, Int, Int) -> Unit,
    playhead: Int,
    flashes: List<Boolean>,
    recording: Boolean,
    onRecToggle: () -> Unit,
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
    onPadReleaseMs: (Float) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(
            text = "SP-1200 Clone",
            style = MaterialTheme.typography.titleLarge,
            color = Color(0xFF4FC3F7)
        )

        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            SmallButton("PADS", view == 0) { onViewChange(0) }
            SmallButton("SEQ", view == 1) { onViewChange(1) }
            SmallButton("EDIT", view == 2) { onViewChange(2) }
            SmallButton("ROLL", view == 3) { onViewChange(3) }
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
        }

        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            listOf("A", "B", "C", "D").forEachIndexed { i, name ->
                SmallButton(name, bank == i) { onBankChange(i) }
            }
            SmallButton(if (recording) "REC*" else "REC", recording) { onRecToggle() }
        }

        Text(
            text = "MIDI: $midiDeviceName",
            color = Color(0xFF888888),
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
                onPadReleaseMs = onPadReleaseMs
            )

            3 -> RollView(
                selectedPad = selectedPad,
                onSelectPad = onSelectPad,
                loadedPads = loadedPads,
                roll = roll,
                onToggleRollCell = onToggleRollCell,
                playhead = playhead,
                playing = playing
            )

            else -> {
                Text(
                    text = "Tap = play. Long press = load WAV. Bank: ${'A' + bank}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFF888888)
                )

                LazyVerticalGrid(
                    columns = GridCells.Fixed(4),
                    modifier = Modifier
                        .fillMaxSize()
                        .weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(8) { index ->
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
fun RollView(
    selectedPad: Int,
    onSelectPad: (Int) -> Unit,
    loadedPads: Set<Int>,
    roll: List<List<Int>>,
    onToggleRollCell: (Int, Int, Int) -> Unit,
    playhead: Int,
    playing: Boolean
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (pad in 0 until 8) {
                val bg = when {
                    pad == selectedPad -> Color.White
                    loadedPads.contains(pad) -> padColor(pad)
                    else -> Color(0xFF2A2A2A)
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
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }

        Text(
            text = "ROLL: notes play selected pad at row pitch (+6..-5)",
            color = Color(0xFF888888),
            style = MaterialTheme.typography.bodySmall
        )

        for (r in 0 until 12) {
            val pitchOff = 6 - r
            val enc = pitchOff + 13

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(3.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(24.dp)
                        .height(22.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = if (pitchOff >= 0) "+$pitchOff" else "$pitchOff",
                        color = Color(0xFF888888),
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                for (step in 0 until 16) {
                    val on = roll[selectedPad][step] == enc
                    val offColor = when {
                        playing && step == playhead -> Color(0xFF5A5A7A)
                        step % 4 == 0 -> Color(0xFF3A3A3A)
                        else -> Color(0xFF262626)
                    }

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(22.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(if (on) padColor(selectedPad) else offColor)
                            .clickable {
                                onToggleRollCell(selectedPad, step, if (on) 0 else enc)
                            }
                    )
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
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        for (pad in 0 until 8) {
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
                        .background(if (mutes[pad]) Color(0xFFB71C1C) else Color(0xFF333333))
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
                        .background(if (solos[pad]) Color(0xFFFDD835) else Color(0xFF333333))
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
                        playing && step == playhead -> Color(0xFF5A5A7A)
                        step % 4 == 0 -> Color(0xFF3A3A3A)
                        else -> Color(0xFF262626)
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
    onPadReleaseMs: (Float) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            for (pad in 0 until 8) {
                val bg = when {
                    pad == selectedPad -> Color.White
                    loadedPads.contains(pad) -> padColor(pad)
                    else -> Color(0xFF2A2A2A)
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
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(100.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0xFF1E1E1E))
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
                        color = Color(0xFF4FC3F7),
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
                .background(Color(0xFF4FC3F7))
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
                color = Color.Black,
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
