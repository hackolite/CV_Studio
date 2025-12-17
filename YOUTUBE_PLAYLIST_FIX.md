# YouTube Node Playlist URL Fix

## Problem
When users paste a YouTube URL that contains a playlist parameter (e.g., `https://www.youtube.com/watch?v=gFRtAAmiFbE&list=PLxtg5zfgORZr8KB1VglBvI6czMJpPL-rx`), the YouTube node fails to display the video. The display doesn't work because yt-dlp tries to extract the entire playlist instead of just the single video.

## Root Cause
The `get_light_live_stream_url()` function in `node/InputNode/node_youtube.py` did not specify the `noplaylist` option in the yt-dlp configuration. When a URL contains a playlist parameter (`&list=...`), yt-dlp's default behavior is to extract the entire playlist, which causes:
1. Longer extraction time
2. Incorrect data structure (playlist info instead of single video info)
3. Failure to display the video in the node

## Solution
Added `"noplaylist": True` to the `ydl_opts` dictionary in the `get_light_live_stream_url()` function. This option tells yt-dlp to:
- Extract only the single video specified in the URL
- Ignore the playlist parameter completely
- Treat the URL as a single video request

## Changes Made

### File: `node/InputNode/node_youtube.py`

**Before:**
```python
ydl_opts = {
    "quiet": True,
    "format": "best[height<=400]",  # Limit to 360p to reduce load
}
```

**After:**
```python
ydl_opts = {
    "quiet": True,
    "format": "best[height<=400]",  # Limit to 360p to reduce load
    "noplaylist": True,  # Extract only the video, ignore playlist parameter
}
```

## Testing

### New Test File: `tests/test_youtube_playlist_url.py`
Created comprehensive tests to verify:
1. The `noplaylist` option is present in the configuration
2. Playlist URL formats are correctly identified
3. The `get_light_live_stream_url()` function properly configures the option

All tests pass successfully:
```
Testing YouTube node playlist URL handling...
============================================================
✓ noplaylist option in ydl_opts passed
✓ playlist URL format validation passed
✓ ydl_opts configuration passed
============================================================
Results: 3 passed, 0 failed
✓ All tests passed!
```

### Existing Tests
All existing YouTube node tests continue to pass:
- `test_youtube_button.py`: 2 tests passed
- `test_youtube_playlist_url.py`: 3 tests passed

## Behavior After Fix

### URLs Now Supported
The YouTube node now correctly handles:
1. Simple video URLs: `https://www.youtube.com/watch?v=VIDEO_ID`
2. Video URLs with playlist parameter: `https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID`
3. Video URLs with playlist and index: `https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&index=N`

### Expected Behavior
When a user pastes any of these URL formats:
1. Only the single video specified by `VIDEO_ID` is extracted
2. The video displays correctly in the YouTube node
3. Playlist information is ignored
4. Processing time remains fast (single video extraction only)

## Impact
This is a minimal, surgical fix that:
- ✅ Solves the reported issue with playlist URLs
- ✅ Maintains backward compatibility with simple URLs
- ✅ Does not affect any other functionality
- ✅ Adds one line of configuration
- ✅ Includes comprehensive test coverage

## User Experience Improvement
Users can now:
- Copy YouTube URLs directly from their browser (which often includes playlist parameters)
- Not worry about manually removing `&list=...` parameters
- Paste URLs from playlists and get the specific video they want
- Experience consistent behavior regardless of URL format
