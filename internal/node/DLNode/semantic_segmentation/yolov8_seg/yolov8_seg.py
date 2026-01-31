#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import copy
import cv2
import numpy as np
import onnxruntime

# Disable cuDNN and use CUDA fallback
os.environ["ORT_CUDA_USE_CUDNN"] = "0"


class YOLOv8Seg(object):
    def __init__(
        self,
        model_path='yolov8n-seg.onnx',
        providers=[
            'CUDAExecutionProvider',
            'CPUExecutionProvider',
        ],
        num_classes=80,  # Number of classes (80 for COCO dataset)
        confidence_threshold=0.25,  # Confidence threshold for detection
    ):
        # Load ONNX model
        self.onnx_session = onnxruntime.InferenceSession(
            model_path,
            providers=providers,
        )

        self.num_classes = num_classes
        self.confidence_threshold = confidence_threshold

        self.input_detail = self.onnx_session.get_inputs()[0]
        self.input_name = self.input_detail.name
        self.output_details = self.onnx_session.get_outputs()
        
        # YOLOv8-seg has two outputs: detection output and segmentation masks
        self.output_name_boxes = self.output_details[0].name  # Boxes output
        self.output_name_masks = self.output_details[1].name if len(self.output_details) > 1 else None  # Mask output
        
        # Input shape for YOLOv8-nano-seg (typically 640x640)
        self.input_shape = self.input_detail.shape[2:4]
        self.input_height = self.input_shape[0]
        self.input_width = self.input_shape[1]

    def __call__(self, image):
        """
        Perform segmentation and return contours
        Args:
            image: Input BGR image
        Returns:
            segmentation_map: Array of binary masks for each detected object
        """
        image_height, image_width = image.shape[:2]
        
        # Preprocess
        input_image = self._preprocess(image)
        
        # Inference
        outputs = self.onnx_session.run(None, {self.input_name: input_image})
        
        # Postprocess to get segmentation masks
        segmentation_map = self._postprocess(
            outputs, 
            image_width, 
            image_height
        )
        
        return segmentation_map

    def _preprocess(self, image):
        """
        Preprocess image for YOLOv8 model
        """
        # Resize image to model input size
        input_image = cv2.resize(
            image,
            (self.input_width, self.input_height),
            interpolation=cv2.INTER_LINEAR
        )
        
        # Convert BGR to RGB
        input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        input_image = input_image.astype(np.float32) / 255.0
        
        # Transpose to CHW format (channels, height, width)
        input_image = np.transpose(input_image, (2, 0, 1))
        
        # Add batch dimension
        input_image = np.expand_dims(input_image, axis=0)
        
        return input_image

    def _postprocess(self, outputs, image_width, image_height):
        """
        Postprocess YOLOv8-seg outputs to get segmentation masks
        Args:
            outputs: Model outputs
            image_width: Original image width
            image_height: Original image height
        Returns:
            segmentation_map: Array of binary masks
        """
        # Extract detection boxes and mask coefficients
        boxes_output = outputs[0]  # Shape: [1, 4+num_classes+32, num_detections] for yolov8n-seg
        
        # For YOLOv8-seg, the output contains:
        # - First 4 values: box coordinates (x, y, w, h)
        # - Next num_classes values: class scores
        # - Last 32 values: mask coefficients
        
        # Squeeze batch dimension and transpose
        boxes_output = np.squeeze(boxes_output)  # [4+num_classes+32, num_detections]
        boxes_output = np.transpose(boxes_output)  # [num_detections, 4+num_classes+32]
        
        # Extract boxes, scores, and class IDs
        boxes = boxes_output[:, :4]  # [num_detections, 4]
        scores = boxes_output[:, 4:4+self.num_classes]  # [num_detections, num_classes]
        max_scores = np.max(scores, axis=1)  # [num_detections]
        class_ids = np.argmax(scores, axis=1)  # [num_detections]
        
        # Filter by confidence threshold
        mask = max_scores > self.confidence_threshold
        
        boxes = boxes[mask]
        max_scores = max_scores[mask]
        class_ids = class_ids[mask]
        
        # If we have mask output (proto masks)
        if self.output_name_masks and len(outputs) > 1:
            proto_masks = outputs[1]  # Shape: [1, 32, 160, 160]
            mask_coefficients = boxes_output[:, 4+self.num_classes:]  # [num_detections, 32]
            mask_coefficients = mask_coefficients[mask]  # Filter by confidence
            
            # Generate segmentation masks
            segmentation_masks = self._generate_masks(
                proto_masks,
                mask_coefficients,
                boxes,
                image_width,
                image_height
            )
        else:
            # If no mask output, create empty segmentation map
            segmentation_masks = np.zeros((1, image_height, image_width), dtype=np.float32)
        
        return segmentation_masks

    def _generate_masks(self, proto_masks, mask_coefficients, boxes, image_width, image_height):
        """
        Generate segmentation masks from proto masks and coefficients
        """
        proto_masks = np.squeeze(proto_masks)  # [32, 160, 160]
        num_masks = mask_coefficients.shape[0]
        
        if num_masks == 0:
            return np.zeros((1, image_height, image_width), dtype=np.float32)
        
        # Matrix multiplication to get masks
        # [num_masks, 32] @ [32, 160, 160] -> [num_masks, 160, 160]
        masks = np.matmul(mask_coefficients, proto_masks.reshape(32, -1))
        masks = masks.reshape(num_masks, proto_masks.shape[1], proto_masks.shape[2])
        
        # Apply sigmoid activation
        masks = 1 / (1 + np.exp(-masks))
        
        # Resize masks to original image size
        resized_masks = []
        for mask in masks:
            resized_mask = cv2.resize(
                mask,
                (image_width, image_height),
                interpolation=cv2.INTER_LINEAR
            )
            # Threshold to binary mask
            resized_mask = (resized_mask > 0.5).astype(np.float32)
            resized_masks.append(resized_mask)
        
        if len(resized_masks) > 0:
            return np.array(resized_masks)
        else:
            return np.zeros((1, image_height, image_width), dtype=np.float32)

    def get_class_num(self):
        """
        Return the number of classes
        """
        return self.num_classes

    def extract_contours(self, segmentation_map):
        """
        Extract contours from segmentation masks
        Args:
            segmentation_map: Array of binary masks
        Returns:
            all_contours: List of contours for each mask
        """
        all_contours = []
        
        for mask in segmentation_map:
            # Convert to uint8 for contour detection
            mask_uint8 = (mask * 255).astype(np.uint8)
            
            # Find contours
            contours, _ = cv2.findContours(
                mask_uint8,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            all_contours.append(contours)
        
        return all_contours


if __name__ == '__main__':
    # Test the model
    cap = cv2.VideoCapture(0)
    
    model_path = 'model/yolov8n-seg.onnx'
    model = YOLOv8Seg(model_path)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Get segmentation masks
        segmentation_map = model(frame)
        
        # Extract and draw contours
        contours_list = model.extract_contours(segmentation_map)
        
        debug_frame = copy.deepcopy(frame)
        for contours in contours_list:
            cv2.drawContours(debug_frame, contours, -1, (0, 255, 0), 2)
        
        cv2.imshow('YOLOv8-Seg', debug_frame)
        
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break
    
    cap.release()
    cv2.destroyAllWindows()
