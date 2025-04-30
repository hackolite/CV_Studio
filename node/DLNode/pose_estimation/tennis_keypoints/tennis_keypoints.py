#!/usr/bin/env python
import copy
import cv2 as cv
import onnxruntime as ort
import numpy as np
class KeypointsProcess(object):

    def __init__(
        self,
        model_path,
        model_complexity,
        enable_segmentation,
        min_detection_confidence,
        min_tracking_confidence,
        providers=None,
    ):
        #self.model = None
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name


    def __call__(self, image):
        image_width, image_height = image.shape[1], image.shape[0]

        # Pre process:BGR->RGB
        input_image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
        orig_h, orig_w = input_image.shape[:2]


        resized_img = cv.resize(input_image, (224, 224))
        img_rgb = cv.cvtColor(resized_img, cv.COLOR_BGR2RGB)
        img_normalized = img_rgb.astype(np.float32) / 255.0
        img_normalized = (img_normalized - 0.5) / 0.5  
        img_transposed = np.transpose(img_normalized, (2, 0, 1))  # (3, 224, 224)
        input_tensor = np.expand_dims(img_transposed, axis=0)  # (1, 3, 224, 224)

        outputs = self.session.run(None, {self.input_name: input_tensor})
        pred_kps = outputs[0].reshape(-1, 2)  # (N, 2)

        scale_x = orig_w / 224
        scale_y = orig_h / 224
        rescaled_kps = pred_kps * np.array([scale_x, scale_y])
        
        return rescaled_kps


class tennis_keypoints(object):

    def __init__(
        self,
        model_path,
        providers=None,
    ):
        self.model = KeypointsProcess(
            model_path=model_path,
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def __call__(self, image):
        return self.model(image)



def draw_landmarks(image, results_list, score_th):
    return image


if __name__ == '__main__':
    cap = cv.VideoCapture(0)

    # Load model
    model = MediaPipePoseComplexity0(None)

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
        cv.imshow('MediaPipe Pose', frame)
    cap.release()
    cv.destroyAllWindows()
