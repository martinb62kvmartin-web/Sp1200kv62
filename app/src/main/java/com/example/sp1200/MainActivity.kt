package com.example.sp1200

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
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

@Composable
fun Sp1200App(onPadDown: (Int) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "SP-1200 Clone MVP",
            style = MaterialTheme.typography.titleLarge,
            color = Color.White
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
                    onPadDown = onPadDown
                )
            }
        }
    }
}

@Composable
fun Pad(index: Int, onPadDown: (Int) -> Unit) {
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
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    onPadDown(index)
                }
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = "PAD ${index + 1}",
            color = Color.Black,
            style = MaterialTheme.typography.titleMedium
        )
    }
}
