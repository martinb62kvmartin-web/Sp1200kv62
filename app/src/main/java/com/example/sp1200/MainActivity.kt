package com.example.sp1200

import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
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
    private external fun nativeLoadSample(padIndex: Int, fd: Int): Boolean

    private var pendingPad by mutableStateOf(-1)
    private var loadedPads by mutableStateOf(setOf<Int>())

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
                        onPadDown = { padIndex ->
                            nativeTriggerPad(padIndex)
                        },
                        onPadLongPress = { padIndex ->
                            pendingPad = padIndex
                            pickSample.launch(arrayOf("audio/*"))
                        },
                        loadedPads = loadedPads
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

@Composable
fun Sp1200App(
    onPadDown: (Int) -> Unit,
    onPadLongPress: (Int) -> Unit,
    loadedPads: Set<Int>
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "SP-1200 Clone",
            style = MaterialTheme.typography.titleLarge,
            color = Color.White
        )

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
                    onPadLongPress = onPadLongPress
                )
            }
        }
    }
}

@Composable
fun Pad(
    index: Int,
    hasSample: Boolean,
    onPadDown: (Int) -> Unit,
    onPadLongPress: (Int) -> Unit
) {
    val color = when (index) {
        0 -> Color(0xFFE53935)
        1 -> Color(0xFFFB8C00)
        2 -> Color(0xFFFDD835)
        3 -> Color(0xFF43A047)
        4 -> Color(0xFF1E88E5)
        5 -> Color(0xFF8E24AA)
        6 -> Color(0xFF00ACC1)
        else -> Color(0xFF546E7A)
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .clip(RoundedCornerShape(20.dp))
            .background(color)
            .pointerInput(index) {
                detectTapGestures(
                    onPress = {
                        onPadDown(index)
                        tryAwaitRelease()
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
