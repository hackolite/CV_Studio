#!/usr/bin/env python
import copy

import cv2 as cv
import numpy as np

from node.DLNode.mediapipe_model_utils import get_model_path


class MediaPipeFaceDetection(object):
    """Face detection using MediaPipe Tasks API (``mp.tasks.vision``)."""

    def __init__(
        self,
        model_path,
        model_selection,
        min_detection_confidence,
        providers=None,
    ):
        import mediapipe as mp

        tflite_path = get_model_path("face_detector_short")
        base_options = mp.tasks.BaseOptions(model_asset_path=tflite_path)
        options = mp.tasks.vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=min_detection_confidence,
        )
        self.detector = mp.tasks.vision.FaceDetector.create_from_options(
            options
        )
        self._mp = mp

    def __call__(self, image):
        image_width, image_height = image.shape[1], image.shape[0]

        # Pre process: BGR -> RGB
        input_image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB, data=input_image
        )

        # Inference
        results = self.detector.detect(mp_image)

        # Post process – produce the same dict format as before
        results_list = []
        for detection in results.detections:
            landmark_dict = {}

            # Keypoints (normalized 0-1 in the new API)
            if detection.keypoints:
                score = (
                    detection.categories[0].score
                    if detection.categories
                    else 1.0
                )
                for idx, kp in enumerate(detection.keypoints):
                    x = min(int(kp.x * image_width), image_width - 1)
                    y = min(int(kp.y * image_height), image_height - 1)
                    landmark_dict[idx] = [x, y, score]

            # Bounding box (pixel coords in the new API)
            bbox = detection.bounding_box
            bbox_xmin = bbox.origin_x
            bbox_ymin = bbox.origin_y
            bbox_xmax = bbox_xmin + bbox.width
            bbox_ymax = bbox_ymin + bbox.height
            landmark_dict['bbox'] = [
                bbox_xmin, bbox_ymin, bbox_xmax, bbox_ymax
            ]

            results_list.append(copy.deepcopy(landmark_dict))

        return results_list


class MediaPipeFaceDetectionModel0(object):
    def __init__(
        self,
        model_path,
        providers=None,
    ):
        self.model = MediaPipeFaceDetection(
            None,
            model_selection=0,
            min_detection_confidence=0.7,
        )

    def __call__(self, image):
        return self.model(image)


class MediaPipeFaceDetectionModel1(object):
    def __init__(
        self,
        model_path,
        providers=None,
    ):
        self.model = MediaPipeFaceDetection(
            None,
            model_selection=1,
            min_detection_confidence=0.7,
        )

    def __call__(self, image):
        return self.model(image)


def draw_landmarks(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(6):
            if score_th > results[id][2]:
                continue
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # バウンディングボックス
        bbox = results.get('bbox', None)
        if bbox is not None:
            image = cv.rectangle(
                image,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                (0, 255, 0),
                thickness=2,
            )

    return image


if __name__ == '__main__':
    cap = cv.VideoCapture(0)

    # Load model
    model = MediaPipeFaceDetectionModel0(None)

    score_th = 0.5

    while True:
        # Capture read
        ret, frame = cap.read()
        if not ret:
            break

        # Inference execution
        results = model(frame)

        # Draw
        frame = draw_landmarks(frame, results, score_th)

        key = cv.waitKey(1)
        if key == 27:  # ESC
            break
        cv.imshow('MediaPipe Hands', frame)
    cap.release()
    cv.destroyAllWindows()
