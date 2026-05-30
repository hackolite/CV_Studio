#!/usr/bin/env python
import copy

import cv2 as cv
import numpy as np

from node.DLNode.mediapipe_model_utils import get_model_path


class MediaPipeFaceMesh(object):
    """Face mesh/landmarks using MediaPipe Tasks API (``mp.tasks.vision``)."""

    def __init__(
        self,
        model_path,
        max_num_faces=5,
        refine_landmarks=False,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        providers=None,
    ):
        import mediapipe as mp

        tflite_path = get_model_path("face_landmarker")
        base_options = mp.tasks.BaseOptions(model_asset_path=tflite_path)
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            num_faces=max_num_faces,
            min_face_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            # Note: The old refine_landmarks option (which added iris landmarks)
            # has no direct equivalent in the new Tasks API.  The FaceLandmarker
            # model already includes iris landmarks by default.
        )
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(
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
        results = self.landmarker.detect(mp_image)

        # Post process – produce the same dict format as before
        results_list = []
        if results.face_landmarks:
            for face_landmarks in results.face_landmarks:
                landmark_dict = {}

                for idx, landmark in enumerate(face_landmarks):
                    x = min(int(landmark.x * image_width), image_width - 1)
                    y = min(int(landmark.y * image_height), image_height - 1)
                    z = landmark.z
                    visibility = 1.0
                    landmark_dict[idx] = [x, y, z, visibility]

                results_list.append(copy.deepcopy(landmark_dict))

        return results_list


class MediaPipeFaceMeshNonRefine(object):
    def __init__(
        self,
        model_path,
        providers=None,
    ):
        self.model = MediaPipeFaceMesh(
            None,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )

    def __call__(self, image):
        return self.model(image)


class MediaPipeFaceMeshRefine(object):
    def __init__(
        self,
        model_path,
        providers=None,
    ):
        self.model = MediaPipeFaceMesh(
            None,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
        )

    def __call__(self, image):
        return self.model(image)


def draw_landmarks(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(len(results)):
            if score_th > results[id][3]:
                continue
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv.circle(image, (landmark_x, landmark_y), 1, (0, 255, 0), -1)

        # 左眉毛(55：内側、46：外側)
        cv.line(image, results[55][:2], results[65][:2], (0, 255, 0), 2)
        cv.line(image, results[65][:2], results[52][:2], (0, 255, 0), 2)
        cv.line(image, results[52][:2], results[53][:2], (0, 255, 0), 2)
        cv.line(image, results[53][:2], results[46][:2], (0, 255, 0), 2)

        # # 右眉毛(285：内側、276：外側)
        cv.line(image, results[285][:2], results[295][:2], (0, 255, 0), 2)
        cv.line(image, results[295][:2], results[282][:2], (0, 255, 0), 2)
        cv.line(image, results[282][:2], results[283][:2], (0, 255, 0), 2)
        cv.line(image, results[283][:2], results[276][:2], (0, 255, 0), 2)

        # # 左目 (133：目頭、246：目尻)
        cv.line(image, results[133][:2], results[173][:2], (0, 255, 0), 2)
        cv.line(image, results[173][:2], results[157][:2], (0, 255, 0), 2)
        cv.line(image, results[157][:2], results[158][:2], (0, 255, 0), 2)
        cv.line(image, results[158][:2], results[159][:2], (0, 255, 0), 2)
        cv.line(image, results[159][:2], results[160][:2], (0, 255, 0), 2)
        cv.line(image, results[160][:2], results[161][:2], (0, 255, 0), 2)
        cv.line(image, results[161][:2], results[246][:2], (0, 255, 0), 2)

        cv.line(image, results[246][:2], results[163][:2], (0, 255, 0), 2)
        cv.line(image, results[163][:2], results[144][:2], (0, 255, 0), 2)
        cv.line(image, results[144][:2], results[145][:2], (0, 255, 0), 2)
        cv.line(image, results[145][:2], results[153][:2], (0, 255, 0), 2)
        cv.line(image, results[153][:2], results[154][:2], (0, 255, 0), 2)
        cv.line(image, results[154][:2], results[155][:2], (0, 255, 0), 2)
        cv.line(image, results[155][:2], results[133][:2], (0, 255, 0), 2)

        # # 右目 (362：目頭、466：目尻)
        cv.line(image, results[362][:2], results[398][:2], (0, 255, 0), 2)
        cv.line(image, results[398][:2], results[384][:2], (0, 255, 0), 2)
        cv.line(image, results[384][:2], results[385][:2], (0, 255, 0), 2)
        cv.line(image, results[385][:2], results[386][:2], (0, 255, 0), 2)
        cv.line(image, results[386][:2], results[387][:2], (0, 255, 0), 2)
        cv.line(image, results[387][:2], results[388][:2], (0, 255, 0), 2)
        cv.line(image, results[388][:2], results[466][:2], (0, 255, 0), 2)

        cv.line(image, results[466][:2], results[390][:2], (0, 255, 0), 2)
        cv.line(image, results[390][:2], results[373][:2], (0, 255, 0), 2)
        cv.line(image, results[373][:2], results[374][:2], (0, 255, 0), 2)
        cv.line(image, results[374][:2], results[380][:2], (0, 255, 0), 2)
        cv.line(image, results[380][:2], results[381][:2], (0, 255, 0), 2)
        cv.line(image, results[381][:2], results[382][:2], (0, 255, 0), 2)
        cv.line(image, results[382][:2], results[362][:2], (0, 255, 0), 2)

        # # 口 (308：右端、78：左端)
        cv.line(image, results[308][:2], results[415][:2], (0, 255, 0), 2)
        cv.line(image, results[415][:2], results[310][:2], (0, 255, 0), 2)
        cv.line(image, results[310][:2], results[311][:2], (0, 255, 0), 2)
        cv.line(image, results[311][:2], results[312][:2], (0, 255, 0), 2)
        cv.line(image, results[312][:2], results[13][:2], (0, 255, 0), 2)
        cv.line(image, results[13][:2], results[82][:2], (0, 255, 0), 2)
        cv.line(image, results[82][:2], results[81][:2], (0, 255, 0), 2)
        cv.line(image, results[81][:2], results[80][:2], (0, 255, 0), 2)
        cv.line(image, results[80][:2], results[191][:2], (0, 255, 0), 2)
        cv.line(image, results[191][:2], results[78][:2], (0, 255, 0), 2)

        cv.line(image, results[78][:2], results[95][:2], (0, 255, 0), 2)
        cv.line(image, results[95][:2], results[88][:2], (0, 255, 0), 2)
        cv.line(image, results[88][:2], results[178][:2], (0, 255, 0), 2)
        cv.line(image, results[178][:2], results[87][:2], (0, 255, 0), 2)
        cv.line(image, results[87][:2], results[14][:2], (0, 255, 0), 2)
        cv.line(image, results[14][:2], results[317][:2], (0, 255, 0), 2)
        cv.line(image, results[317][:2], results[402][:2], (0, 255, 0), 2)
        cv.line(image, results[402][:2], results[318][:2], (0, 255, 0), 2)
        cv.line(image, results[318][:2], results[324][:2], (0, 255, 0), 2)
        cv.line(image, results[324][:2], results[308][:2], (0, 255, 0), 2)

    return image


if __name__ == '__main__':
    cap = cv.VideoCapture(0)

    # Load model
    model = MediaPipeFaceMeshRefine(None)

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
