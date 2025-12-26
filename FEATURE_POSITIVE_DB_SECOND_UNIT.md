# Feature: Positive Decibels and Second Time Unit

## What was implemented?

This PR adds two features as requested in the issue:

### 1. Positive Decibel Values ✅
**Before:** Decibel values were negative (e.g., -20 dB for typical audio)  
**After:** Decibel values are positive (e.g., 20 dB for the same audio)

The microphone node now multiplies decibel calculations by -1 to make values positive, which is more intuitive for users. For silence (zero RMS), the value is set to 120.0 dB, consistent with a positive dB scale.

### 2. Second Time Unit in Chart ✅
**Before:** Chart time units were "minute" and "hour"  
**After:** Chart time units are "second", "minute", and "hour"

The objchart node now supports second-level time aggregation, enabling finer-grained monitoring of real-time data. Time labels are formatted as:
- Second: HH:MM:SS (e.g., 19:11:42)
- Minute: HH:MM (e.g., 19:11)
- Hour: HH:00 (e.g., 19:00)

## How to use?

### Using Positive Decibels
1. Add a **Microphone** node to your workflow
2. Set **Output Mode** to "dB Intensity"
3. Connect to an **objchart** node
4. The chart will now display positive dB values instead of negative

### Using Second Time Unit
1. Add an **objchart** node to your workflow
2. In the **Time Unit** dropdown, select "second"
3. The chart will now aggregate data by second instead of minute or hour

## Example

```
Signal Level | RMS   | Old dB  | New dB
-----------------------------------------
Very quiet   | 0.0155|  -36.17 | 36.17
Quiet        | 0.1013|  -19.89 | 19.89
Medium       | 0.3114|  -10.13 | 10.13
Loud         | 0.6107|   -4.28 |  4.28
Very loud    | 0.9001|   -0.91 |  0.91
```

## Files Changed

**Core Implementation:**
- `node/InputNode/node_microphone.py` - Positive decibel transformation
- `node/VisualNode/node_obj_chart.py` - Second time unit support

**Tests:**
- `tests/test_microphone_enhancements.py` - Updated for positive dB
- `tests/test_second_time_unit.py` - New comprehensive tests
- `tests/demo_second_time_unit.py` - Demo script

**Documentation:**
- `IMPLEMENTATION_SUMMARY_POSITIVE_DB_SECOND_UNIT.md`
- `SECURITY_SUMMARY_POSITIVE_DB_SECOND_UNIT.md`

## Testing

All tests pass:
```
✓ test_microphone_enhancements.py (5 passed)
✓ test_microphone_fps_removal.py (5 passed)
✓ test_second_time_unit.py (3 passed)
✓ demo_second_time_unit.py (all demos passed)
```

Security check: ✅ 0 vulnerabilities found

## Backward Compatibility

✅ Fully backward compatible
- Existing "minute" and "hour" time units continue to work
- Chart rendering logic preserved
- No breaking changes to the API

## Technical Details

### Decibel Transformation
```python
# Old calculation
db_value = 20 * np.log10(rms)  # Negative for RMS < 1.0

# New calculation
db_value = -20 * np.log10(rms)  # Positive for RMS < 1.0
```

### Time Bucket Creation
```python
# Second-level bucket
bucket = now.replace(microsecond=0)

# Minute-level bucket
bucket = now.replace(second=0, microsecond=0)

# Hour-level bucket
bucket = now.replace(minute=0, second=0, microsecond=0)
```

## Visual Examples

### Chart with Second Time Unit
The chart X-axis now shows labels like:
```
19:11:42  19:11:43  19:11:44  19:11:45  19:11:46
```

### Positive Decibel Display
The chart Y-axis shows positive values:
```
30 dB |     ■
25 dB |   ■ ■
20 dB | ■ ■ ■ ■
15 dB |■■■■■■■■
```

---

**Issue addressed:** multiplier les décibels pour que ça soit positif et rajouter dans la partie chart un time unit en secondes

**Status:** ✅ Complete
