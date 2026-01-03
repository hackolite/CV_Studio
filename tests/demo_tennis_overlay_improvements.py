#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual demonstration of TennisCourt BGRA transparency and ImageOverlay functionality.
This creates visual examples showing the improvements.
"""
import numpy as np
import cv2
import os


def create_tennis_court_bgra():
    """Create a simple tennis court visualization with BGRA transparency"""
    # Create BGRA image (transparent background)
    width, height = 600, 800
    court_img = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Tennis court parameters (simplified)
    court_width_m = 10.97
    court_length_m = 23.77
    scale = 15  # pixels per meter
    offset_x = int((width - court_width_m * scale) / 2)
    offset_y = int((height - court_length_m * scale) / 2)
    
    # Draw green court with alpha
    court_w_px = int(court_width_m * scale)
    court_l_px = int(court_length_m * scale)
    cv2.rectangle(court_img, 
                 (offset_x, offset_y),
                 (offset_x + court_w_px, offset_y + court_l_px),
                 (0, 150, 0, 255), -1)  # Green with full opacity
    
    # Draw white lines (BGRA)
    line_color = (255, 255, 255, 255)
    
    # Outer boundary
    cv2.rectangle(court_img,
                 (offset_x, offset_y),
                 (offset_x + court_w_px, offset_y + court_l_px),
                 line_color, 2)
    
    # Center line (net)
    net_y = offset_y + court_l_px // 2
    cv2.line(court_img, (offset_x, net_y), (offset_x + court_w_px, net_y), line_color, 2)
    
    # Service lines (horizontal lines)
    service_dist = int(6.4 * scale)  # Approximate
    cv2.line(court_img, (offset_x, offset_y + service_dist),
            (offset_x + court_w_px, offset_y + service_dist), line_color, 2)
    cv2.line(court_img, (offset_x, offset_y + court_l_px - service_dist),
            (offset_x + court_w_px, offset_y + court_l_px - service_dist), line_color, 2)
    
    # Center service line (vertical)
    center_x = offset_x + court_w_px // 2
    cv2.line(court_img, (center_x, offset_y + service_dist),
            (center_x, offset_y + court_l_px - service_dist), line_color, 2)
    
    # Add yellow player markers
    player_color = (0, 255, 255, 255)  # Yellow in BGRA
    cv2.circle(court_img, (center_x - 30, net_y - 40), 8, player_color, -1)
    cv2.circle(court_img, (center_x + 30, net_y + 40), 8, player_color, -1)
    
    return court_img


def create_master_image():
    """Create a master image for overlay demonstration"""
    master = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Create a gradient background
    for y in range(480):
        for x in range(640):
            master[y, x] = (int(x * 255 / 640), int(y * 255 / 480), 128)
    
    # Add some text
    cv2.putText(master, "Master Image", (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return master


def overlay_with_alpha_blending(master, overlay, x, y, width=0, height=0, alpha=1.0):
    """Overlay BGRA image onto BGR master with proper alpha blending"""
    if width > 0 or height > 0:
        overlay_h, overlay_w = overlay.shape[:2]
        if width > 0 and height == 0:
            height = int(overlay_h * width / overlay_w)
        elif height > 0 and width == 0:
            width = int(overlay_w * height / overlay_h)
        overlay = cv2.resize(overlay, (width, height), interpolation=cv2.INTER_AREA)
    
    overlay_h, overlay_w = overlay.shape[:2]
    master_h, master_w = master.shape[:2]
    
    # Calculate clipping
    overlay_x1, overlay_y1 = 0, 0
    overlay_x2, overlay_y2 = overlay_w, overlay_h
    master_x1, master_y1 = x, y
    master_x2, master_y2 = x + overlay_w, y + overlay_h
    
    if master_x1 < 0:
        overlay_x1 = -master_x1
        master_x1 = 0
    if master_y1 < 0:
        overlay_y1 = -master_y1
        master_y1 = 0
    if master_x2 > master_w:
        overlay_x2 = overlay_w - (master_x2 - master_w)
        master_x2 = master_w
    if master_y2 > master_h:
        overlay_y2 = overlay_h - (master_y2 - master_h)
        master_y2 = master_h
    
    if master_x1 >= master_x2 or master_y1 >= master_y2:
        return master
    
    # Extract regions
    overlay_region = overlay[overlay_y1:overlay_y2, overlay_x1:overlay_x2]
    master_region = master[master_y1:master_y2, master_x1:master_x2]
    
    # Alpha blending
    if overlay_region.shape[2] == 4:
        overlay_alpha = overlay_region[:, :, 3:4] / 255.0 * alpha
        overlay_bgr = overlay_region[:, :, :3]
        blended = (overlay_bgr * overlay_alpha + master_region * (1 - overlay_alpha)).astype(np.uint8)
    else:
        blended = cv2.addWeighted(overlay_region, alpha, master_region, 1 - alpha, 0)
    
    result = master.copy()
    result[master_y1:master_y2, master_x1:master_x2] = blended
    
    return result


def main():
    print("=" * 70)
    print("Visual Demonstration: TennisCourt BGRA + ImageOverlay")
    print("=" * 70)
    print()
    
    output_dir = '/tmp/tennis_overlay_demo'
    os.makedirs(output_dir, exist_ok=True)
    
    # Demo 1: Tennis court with transparency
    print("Demo 1: Creating TennisCourt with BGRA transparency...")
    court = create_tennis_court_bgra()
    
    # Save as PNG (preserves alpha channel)
    court_path = os.path.join(output_dir, '1_tennis_court_bgra.png')
    cv2.imwrite(court_path, court)
    print(f"  ✓ Saved: {court_path}")
    print(f"    Shape: {court.shape} (4 channels = BGRA)")
    
    # Show alpha channel
    alpha_channel = court[:, :, 3]
    alpha_viz = cv2.cvtColor(alpha_channel, cv2.COLOR_GRAY2BGR)
    alpha_path = os.path.join(output_dir, '1_alpha_channel.png')
    cv2.imwrite(alpha_path, alpha_viz)
    print(f"  ✓ Saved alpha channel: {alpha_path}")
    print()
    
    # Demo 2: Overlay tennis court on master image (centered)
    print("Demo 2: Overlaying tennis court on master image (centered)...")
    master = create_master_image()
    result = overlay_with_alpha_blending(master, court, 20, 0, width=300, height=400)
    
    result_path = os.path.join(output_dir, '2_overlay_centered.png')
    cv2.imwrite(result_path, result)
    print(f"  ✓ Saved: {result_path}")
    print(f"    Position: (20, 0), Size: 300x400")
    print()
    
    # Demo 3: Partial overlay (left edge)
    print("Demo 3: Partial overlay at left edge (x = -150)...")
    result = overlay_with_alpha_blending(master, court, -150, 50, width=300, height=400)
    
    result_path = os.path.join(output_dir, '3_overlay_left_edge.png')
    cv2.imwrite(result_path, result)
    print(f"  ✓ Saved: {result_path}")
    print(f"    Position: (-150, 50) - half visible")
    print()
    
    # Demo 4: Partial overlay (right edge)
    print("Demo 4: Partial overlay at right edge (x = 490)...")
    result = overlay_with_alpha_blending(master, court, 490, 50, width=300, height=400)
    
    result_path = os.path.join(output_dir, '4_overlay_right_edge.png')
    cv2.imwrite(result_path, result)
    print(f"  ✓ Saved: {result_path}")
    print(f"    Position: (490, 50) - half visible")
    print()
    
    # Demo 5: Different sizes
    print("Demo 5: Different overlay sizes...")
    
    # Small
    result_small = overlay_with_alpha_blending(master, court, 450, 50, width=150, height=200)
    small_path = os.path.join(output_dir, '5_overlay_small.png')
    cv2.imwrite(small_path, result_small)
    print(f"  ✓ Saved small (150x200): {small_path}")
    
    # Large
    result_large = overlay_with_alpha_blending(master, court, 50, 20, width=500, height=440)
    large_path = os.path.join(output_dir, '5_overlay_large.png')
    cv2.imwrite(large_path, result_large)
    print(f"  ✓ Saved large (500x440): {large_path}")
    print()
    
    # Demo 6: Transparency levels
    print("Demo 6: Different transparency levels...")
    
    # 100% opaque
    result_100 = overlay_with_alpha_blending(master, court, 20, 40, width=200, height=267, alpha=1.0)
    path_100 = os.path.join(output_dir, '6_alpha_100.png')
    cv2.imwrite(path_100, result_100)
    print(f"  ✓ Saved 100% opacity: {path_100}")
    
    # 50% transparent
    result_50 = overlay_with_alpha_blending(master, court, 240, 40, width=200, height=267, alpha=0.5)
    path_50 = os.path.join(output_dir, '6_alpha_50.png')
    cv2.imwrite(path_50, result_50)
    print(f"  ✓ Saved 50% opacity: {path_50}")
    
    # 25% transparent
    result_25 = overlay_with_alpha_blending(master, court, 460, 40, width=180, height=240, alpha=0.25)
    path_25 = os.path.join(output_dir, '6_alpha_25.png')
    cv2.imwrite(path_25, result_25)
    print(f"  ✓ Saved 25% opacity: {path_25}")
    print()
    
    print("=" * 70)
    print("All demonstrations completed successfully! ✓")
    print("=" * 70)
    print()
    print(f"Output directory: {output_dir}")
    print()
    print("Generated files:")
    for filename in sorted(os.listdir(output_dir)):
        filepath = os.path.join(output_dir, filename)
        print(f"  • {filename} ({os.path.getsize(filepath)} bytes)")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
