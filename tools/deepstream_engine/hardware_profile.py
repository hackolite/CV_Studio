"""
Hardware profile for the target deployment platform.

Default target: NVIDIA RTX 5070
  - 16 GB VRAM (GDDR7)
  - 32 GB system RAM
  - Blackwell architecture (SM 100)
  - TensorRT 10.x support
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareProfile:
    """Target hardware specifications for DeepStream optimization."""

    name: str = "RTX_5070"
    gpu_arch: str = "sm_100"  # Blackwell
    vram_gb: int = 16
    system_ram_gb: int = 32
    max_batch_size: int = 8
    tensorrt_workspace_mb: int = 4096  # 4 GB TRT workspace (safe for 16 GB VRAM)
    fp16_enabled: bool = True
    int8_enabled: bool = False  # Requires calibration data
    dla_enabled: bool = False  # DLA not available on desktop GPUs
    num_cuda_streams: int = 4
    # DeepStream tuning
    nvbuf_memory_type: int = 0  # 0 = NVBUF_MEM_DEFAULT (GPU mapped)
    gpu_id: int = 0
    # Batched inference optimization
    infer_interval: int = 1  # Process every frame
    max_simultaneous_streams: int = 8  # With 16GB VRAM


# Singleton for the default target
RTX_5070_PROFILE = HardwareProfile()


def get_profile(name: str = "RTX_5070") -> HardwareProfile:
    """Return a hardware profile by name."""
    profiles = {
        "RTX_5070": HardwareProfile(),
        "RTX_5070_HIGH_BATCH": HardwareProfile(
            name="RTX_5070_HIGH_BATCH",
            max_batch_size=16,
            tensorrt_workspace_mb=6144,
            max_simultaneous_streams=4,
        ),
        "RTX_5070_INT8": HardwareProfile(
            name="RTX_5070_INT8",
            int8_enabled=True,
            max_batch_size=16,
            tensorrt_workspace_mb=4096,
        ),
    }
    return profiles.get(name, RTX_5070_PROFILE)
