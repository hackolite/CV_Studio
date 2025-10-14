        # Update spectrogram display if toggle is enabled
        tag_node_spectrogram_toggle = tag_node_name + ':SpectrogramToggle'
        tag_node_spectrogram_value = tag_node_name + ':SpectrogramValue'
        
        if dpg.does_item_exist(tag_node_spectrogram_toggle):
            show_spectrogram = dpg_get_value(tag_node_spectrogram_toggle)
            if show_spectrogram and str(node_id) in self._spectrogram_array:
                # Get the full spectrogram array
                full_spectrogram = self._spectrogram_array[str(node_id)]
                
                # Calculate current playback position and extract scrolling window
                if str(node_id) in self._spectrogram_meta and video_capture is not None:
                    meta = self._spectrogram_meta[str(node_id)]
                    fps = meta['fps']
                    sr = meta['sr']
                    hop_length = meta['hop_length']
                    
                    # Get current frame position
                    current_frame = self._frame_count.get(str(node_id), 0)
                    
                    # Calculate current time in seconds
                    current_time = current_frame / fps if fps > 0 else 0
                    
                    # Calculate spectrogram column position
                    current_sample = int(current_time * sr)
                    spectrogram_col = int(current_sample / hop_length)
                    
                    # Define scrolling window size (2 seconds)
                    window_duration = 2.0  # seconds
                    window_cols = int((window_duration * sr) / hop_length)
                    
                    # Calculate window boundaries centered on current position
                    window_start = max(0, spectrogram_col - window_cols // 2)
                    window_end = min(full_spectrogram.shape[1], window_start + window_cols)
                    
                    # Adjust window_start if we're near the end
                    if window_end == full_spectrogram.shape[1]:
                        window_start = max(0, window_end - window_cols)
                    
                    # Extract the scrolling window
                    spectrogram_window = full_spectrogram[:, window_start:window_end].copy()
                    
                    # If window is smaller than expected, pad with black
                    if spectrogram_window.shape[1] < window_cols:
                        padded = np.zeros((full_spectrogram.shape[0], window_cols, 3), dtype=np.uint8)
                        padded[:, :spectrogram_window.shape[1], :] = spectrogram_window
                        spectrogram_window = padded
                    
                    # Draw yellow line at center to show current position
                    center_col = min((spectrogram_col - window_start), spectrogram_window.shape[1] - 1)
                    if 0 <= center_col < spectrogram_window.shape[1]:
                        cv2.line(spectrogram_window, 
                                (center_col, 0), 
                                (center_col, spectrogram_window.shape[0] - 1), 
                                (0, 255, 255), 2)
                    
                    # Convert to DPG texture format and update
                    texture = self.convert_cv_to_dpg(
                        spectrogram_window,
                        small_window_w,
                        small_window_h
                    )
                    dpg_set_value(tag_node_spectrogram_value, texture)
                else:
                    # Fallback: show full spectrogram if metadata not available
                    texture = self.convert_cv_to_dpg(
                        full_spectrogram,
                        small_window_w,
                        small_window_h
                    )
                    dpg_set_value(tag_node_spectrogram_value, texture)
