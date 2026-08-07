package com.example.sp1200

import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp

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
    private external fun nativeLoadSample(padIndex: Int, fd: Int): Boolean
    private external fun nativeSeqSetPlaying(playing: Boolean)
    private external fun nativeSeqSetBpm(bpm: Float)
    private external fun nativeSeqSetSwing(swing: Float)
    private external fun nativeSeqSetMask(padIndex: Int, mask: Int)

    private var pendingPad by mutableStateOf(-1)
    private var loadedPads by mutableStateOf(setOf<Int>())
    private var gateMode by mutableStateOf(false)
    private var pitch by mutableStateOf(0f)
    private var viewSeq by mutableStateOf(false)
    private var playing by mutableStateOf(false)
    private var bpm by mutableStateOf(90f)
    private var swing by mutableStateOf(0f)
    private var pattern by mutableStateOf(List(8) { 0 })

    private val pickSample =
        registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
            val pad = pendingPad
            pendingPad = -1

            if (uri != null && pad >= 0) {
                contentResolver.openFileDescriptor(uri, "r")?.use { pfd ->
                    val ok = nativeLoadSample(pad, pfd.fd)
                    if (ok) {
                        loadedPads = loadedPads + pad
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

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF111111)
                ) {
                    Sp1200App(
                        onPadDown = { nativeTriggerPad(it) },
                        onPadUp = { nativePadRelease(it) },
                        onPadLongPress = { pad ->
                            pendingPad = pad
                            pickSample.launch(arrayOf("audio/*"))
                        },
                        loadedPads = loadedPads,
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
                        viewSeq = viewSeq,
                        onViewChange = { viewSeq = it },
                        playing = playing,
                        onPlayToggle = {
                            playing = !playing
                            nativeSeqSetPlaying(playing)
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
                        pattern = pattern,
                        onToggleStep = { pad, step ->
                            val newMask = pattern[pad] xor (1 shl step)
                            pattern = pattern.toMutableList().also { it[pad] = newMask }
                            nativeSeqSetMask(pad, newMask)
                        }
                    )
                }
            }
        }
    }

    override fun onStart() {
        super.onStart()
        nativeStart()
    }

    override fun onStop() {
        super.onStop()
        nativeStop()
    }

    override fun onDestroy() {
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
fun Sp1200App(
    onPadDown: (Int) -> Unit,
    onPadUp: (Int) -> Unit,
    onPadLongPress: (Int) -> Unit,
    loadedPads: Set<Int>,
    gateMode: Boolean,
    onGateModeChange: (Boolean) -> Unit,
    pitch: Float,
    onPitchChange: (Float) -> Unit,
    viewSeq: Boolean,
    onViewChange: (Boolean) -> Unit,
    playing: Boolean,
    onPlayToggle: () -> Unit,
    bpm: Float,
    onBpmChange: (Float) -> Unit,
    swing: Float,
    onSwingChange: (Float) -> Unit,
    pattern: List<Int>,
    onToggleStep: (Int, Int) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text(
            text = "SP-1200 Clone",
            style = MaterialTheme.typography.titleLarge,
            color = Color.White
        )

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Button(onClick = { onViewChange(!viewSeq) }) {
                Text(if (viewSeq) "PADS" else "SEQ")
            }
            Button(onClick = onPlayToggle) {
                Text(if (playing) "STOP" else "PLAY")
            }
            Button(onClick = { onGateModeChange(!gateMode) }) {
                Text(if (gateMode) "GATE" else "SHOT")
            }
        }

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

            if (viewSeq) {
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

        if (viewSeq) {
            SequencerGrid(
                pattern = pattern,
                onToggleStep = onToggleStep
            )
        } else {
            Text(
                text = "Tap = play. Long press = load WAV",
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
                        onPadDown = onPadDown,
                        onPadUp = onPadUp,
                        onPadLongPress = onPadLongPress
                    )
                }
            }
        }
    }
}

@Composable
fun SequencerGrid(
    pattern: List<Int>,
    onToggleStep: (Int, Int) -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        for (pad in 0 until 8) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(3.dp)
            ) {
                for (step in 0 until 16) {
                    val on = (pattern[pad] ushr step) and 1 == 1
                    val offColor = if (step % 4 == 0) Color(0xFF3A3A3A) else Color(0xFF262626)

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
fun Pad(
    index: Int,
    hasSample: Boolean,
    onPadDown: (Int) -> Unit,
    onPadUp: (Int) -> Unit,
    onPadLongPress: (Int) -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .clip(RoundedCornerShape(20.dp))
            .background(padColor(index))
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
