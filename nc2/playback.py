"""
Animation playback controller. Schedules frame advances via tkinter's
after() mechanism and drives all open plot windows through the manager.
"""

from .constants import (
    PLAYBACK_MIN_INTERVAL_MS,
    PLAYBACK_MAX_INTERVAL_MS,
    PLAYBACK_DEFAULT_INTERVAL_MS,
    PLAYBACK_STEP_MS,
)


class PlaybackMode:
    """Enum-like constants for loop behavior."""
    LOOP = "loop"         # Wrap around from end to start
    BOUNCE = "bounce"     # Reverse direction at boundaries
    ONCE = "once"         # Stop at the end


class PlaybackController:
    """
    Manages time-stepping through a dimension (usually time) and pushes
    updates to all registered plot windows via a callback.

    The controller does not know about the data layer directly. It only
    tracks the current index and calls the provided on_frame callback
    when it's time to advance.
    """

    def __init__(self, root, num_frames, on_frame):
        """
        Args:
            root: tkinter root window (needed for after() scheduling)
            num_frames: total number of frames in the dimension
            on_frame: callback(frame_index) called each time the frame advances
        """
        self._root = root
        self.num_frames = num_frames
        self.on_frame = on_frame

        self.current_frame = 0
        self.interval_ms = PLAYBACK_DEFAULT_INTERVAL_MS
        self.mode = PlaybackMode.LOOP
        self.direction = 1  # +1 forward, -1 reverse

        self._playing = False
        self._after_id = None

    @property
    def playing(self):
        return self._playing

    @property
    def speed_label(self):
        """Human-readable speed string (frames per second)."""
        fps = 1000.0 / self.interval_ms if self.interval_ms > 0 else 0
        return f"{fps:.1f} fps"

    # ------------------------------------------------------------------
    # Transport controls
    # ------------------------------------------------------------------

    def play(self):
        """Start or resume forward playback."""
        self.direction = 1
        if not self._playing:
            self._playing = True
            self._schedule_next()

    def play_reverse(self):
        """Start or resume reverse playback."""
        self.direction = -1
        if not self._playing:
            self._playing = True
            self._schedule_next()

    def pause(self):
        """Pause playback without resetting position."""
        self._playing = False
        self._cancel_scheduled()

    def stop(self):
        """Stop playback and reset to frame 0."""
        self._playing = False
        self._cancel_scheduled()
        self.current_frame = 0
        self.direction = 1
        self.on_frame(self.current_frame)

    def step_forward(self):
        """Advance one frame forward (while paused)."""
        self.pause()
        self._advance(1)
        self.on_frame(self.current_frame)

    def step_backward(self):
        """Step one frame backward (while paused)."""
        self.pause()
        self._advance(-1)
        self.on_frame(self.current_frame)

    def seek(self, frame_idx):
        """Jump to a specific frame index."""
        self.current_frame = max(0, min(frame_idx, self.num_frames - 1))
        self.on_frame(self.current_frame)

    # ------------------------------------------------------------------
    # Speed control
    # ------------------------------------------------------------------

    def speed_up(self):
        """Decrease interval (faster playback)."""
        self.interval_ms = max(
            PLAYBACK_MIN_INTERVAL_MS,
            self.interval_ms - PLAYBACK_STEP_MS,
        )

    def speed_down(self):
        """Increase interval (slower playback)."""
        self.interval_ms = min(
            PLAYBACK_MAX_INTERVAL_MS,
            self.interval_ms + PLAYBACK_STEP_MS,
        )

    def set_speed_ms(self, ms):
        """Set interval directly in milliseconds."""
        self.interval_ms = max(
            PLAYBACK_MIN_INTERVAL_MS,
            min(PLAYBACK_MAX_INTERVAL_MS, ms),
        )

    # ------------------------------------------------------------------
    # Mode control
    # ------------------------------------------------------------------

    def set_mode(self, mode):
        """Set loop mode (loop, bounce, or once)."""
        self.mode = mode

    def set_num_frames(self, n):
        """Update frame count (e.g., when a new variable is selected)."""
        self.num_frames = n
        if self.current_frame >= n:
            self.current_frame = 0

    # ------------------------------------------------------------------
    # Internal scheduling
    # ------------------------------------------------------------------

    def _schedule_next(self):
        """Queue the next frame advance."""
        if self._playing:
            self._after_id = self._root.after(self.interval_ms, self._tick)

    def _cancel_scheduled(self):
        """Cancel any pending scheduled callback."""
        if self._after_id is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self):
        """Called on each scheduled interval to advance the frame."""
        if not self._playing:
            return

        self._advance(self.direction)
        self.on_frame(self.current_frame)
        self._schedule_next()

    def _advance(self, step):
        """
        Move current_frame by step, respecting boundaries and loop mode.
        """
        next_frame = self.current_frame + step

        if next_frame >= self.num_frames:
            if self.mode == PlaybackMode.LOOP:
                next_frame = 0
            elif self.mode == PlaybackMode.BOUNCE:
                self.direction = -1
                next_frame = self.num_frames - 2
            else:  # ONCE
                next_frame = self.num_frames - 1
                self._playing = False

        elif next_frame < 0:
            if self.mode == PlaybackMode.LOOP:
                next_frame = self.num_frames - 1
            elif self.mode == PlaybackMode.BOUNCE:
                self.direction = 1
                next_frame = 1
            else:  # ONCE
                next_frame = 0
                self._playing = False

        self.current_frame = max(0, min(next_frame, self.num_frames - 1))
