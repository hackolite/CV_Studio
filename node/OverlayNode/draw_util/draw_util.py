import copy

import cv2
import numpy as np


def get_class_name(class_id, class_names):
    """
    Safely get class name from class_names, handling both dict and list formats.
    
    Args:
        class_id: The class ID (will be converted to int)
        class_names: Dictionary or list of class names
        
    Returns:
        Class name string, or fallback 'class_N' if not found
    """
    class_id_int = int(class_id)
    if isinstance(class_names, dict):
        return class_names.get(class_id_int, f"class_{class_id_int}")
    elif isinstance(class_names, list) and 0 <= class_id_int < len(class_names):
        return class_names[class_id_int]
    else:
        return f"class_{class_id_int}"


def draw_info(node_name, node_result, image):
    classification_nodes = ['Classification']
    object_detection_nodes = ['ObjectDetection']
    semantic_segmentation_nodes = ['SemanticSegmentation']
    pose_estimation_nodes = ['PoseEstimation']
    face_detection_nodes = ['FaceDetection']
    multi_object_tracking_nodes = ['MultiObjectTracking']
    qr_code_detection_nodes = ['QRCodeDetection']

    debug_image = copy.deepcopy(image)
    if node_name in classification_nodes:
        use_object_detection = node_result.get('use_object_detection', [])
        class_ids = node_result.get('class_ids', [])
        class_scores = node_result.get('class_scores', [])
        class_names = node_result.get('class_names', [])

        if use_object_detection:
            od_bboxes = node_result.get('od_bboxes', [])
            od_scores = node_result.get('od_scores', [])
            od_class_ids = node_result.get('od_class_ids', [])
            od_class_names = node_result.get('od_class_names', [])
            od_score_th = node_result.get('od_score_th', [])
            debug_image = draw_classification_with_od_info(
                debug_image,
                class_ids,
                class_scores,
                class_names,
                od_bboxes,
                od_scores,
                od_class_ids,
                od_class_names,
                od_score_th,
                thickness=3,
            )
        else:
            debug_image = draw_classification_info(
                debug_image,
                class_ids,
                class_scores,
                class_names,
            )
    elif node_name in object_detection_nodes:
        bboxes = node_result.get('bboxes', [])
        scores = node_result.get('scores', [])
        class_ids = node_result.get('class_ids', [])
        class_names = node_result.get('class_names', [])
        score_th = node_result.get('score_th', [])
        debug_image = draw_object_detection_info(
            debug_image,
            score_th,
            bboxes,
            scores,
            class_ids,
            class_names,
        )
    elif node_name in semantic_segmentation_nodes:
        class_num = node_result.get('class_num', [])
        segmentation_map = node_result.get('segmentation_map', [])
        score_th = node_result.get('score_th', [])
        debug_image = draw_semantic_segmentation_info(
            debug_image,
            score_th,
            class_num,
            segmentation_map,
        )
    elif node_name in pose_estimation_nodes:
        model_name = node_result.get('model_name', [])
        results_list = node_result.get('results_list', [])
        score_th = node_result.get('score_th', [])
        debug_image = draw_pose_estimation_info(
            model_name,
            debug_image,
            results_list,
            score_th,
        )
    elif node_name in face_detection_nodes:
        model_name = node_result.get('model_name', [])
        results_list = node_result.get('results_list', [])
        score_th = node_result.get('score_th', [])
        debug_image = draw_face_detection_info(
            model_name,
            debug_image,
            results_list,
            score_th,
        )
    elif node_name in multi_object_tracking_nodes:
        track_ids = node_result.get('track_ids', [])
        bboxes = node_result.get('bboxes', [])
        scores = node_result.get('scores', [])
        class_ids = node_result.get('class_ids', [])
        class_names = node_result.get('class_names', [])
        track_id_dict = node_result.get('track_id_dict', [])
        debug_image = draw_multi_object_tracking_info(
            debug_image,
            track_ids,
            bboxes,
            scores,
            class_ids,
            class_names,
            track_id_dict,
        )
    elif node_name in qr_code_detection_nodes:
        texts = node_result.get('texts', [])
        bboxes = node_result.get('bboxes', [])
        debug_image = draw_qrcode_detection_info(
            debug_image,
            texts,
            bboxes,
        )

    return debug_image


def get_color(index):
    temp_index = abs(int(index + 35)) * 3
    color = (
        (29 * temp_index) % 255,
        (17 * temp_index) % 255,
        (37 * temp_index) % 255,
    )
    return color


def get_color_map_list(num_classes, custom_color=None):
    num_classes += 1
    color_map = num_classes * [0, 0, 0]
    for i in range(0, num_classes):
        j = 0
        lab = i
        while lab:
            color_map[i * 3 + 2] |= (((lab >> 0) & 1) << (7 - j))
            color_map[i * 3 + 1] |= (((lab >> 1) & 1) << (7 - j))
            color_map[i * 3] |= (((lab >> 2) & 1) << (7 - j))
            j += 1
            lab >>= 3
    color_map = color_map[3:]

    if custom_color:
        color_map[:len(custom_color)] = custom_color
    return color_map


def draw_classification_info(
    image,
    class_ids,
    class_scores,
    class_names,
):
    debug_image = copy.deepcopy(image)
    for index, (class_score,
                class_id) in enumerate(zip(class_scores, class_ids)):
        score = '%.2f' % class_score
        class_name = get_class_name(class_id, class_names)
        text = '%s:%s(%s)' % (str(class_id), str(class_name), score)
        debug_image = cv2.putText(
            debug_image,
            text,
            (15, 30 + (index * 35)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            thickness=3,
        )

    return debug_image


def draw_object_detection_info(
    image,
    score_th,
    bboxes,
    scores,
    class_ids,
    class_names,
    thickness=3,
):
    debug_image = copy.deepcopy(image)
    print("external :", debug_image.shape)
    for bbox, score, class_id in zip(bboxes, scores, class_ids):
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

        if score_th > score:
            continue

        color = get_color(class_id)

        # バウンディングボックス
        debug_image = cv2.rectangle(
            debug_image,
            (x1, y1),
            (x2, y2),
            color,
            thickness=thickness,
        )

        # クラスID、スコア
        score = '%.2f' % score
        class_name = get_class_name(class_id, class_names)
        text = '%s:%s(%s)' % (int(class_id), str(class_name), score)
        debug_image = cv2.putText(
            debug_image,
            text,
            (x1, y1 - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=thickness,
        )

    return debug_image


def draw_classification_with_od_info(
    image,
    class_id_list,
    score_list,
    class_name_dict,
    od_bboxes,
    od_scores,
    od_class_ids,
    od_class_names,
    od_score_th,
    thickness=3,
):
    debug_image = copy.deepcopy(image)

    for class_id, score, od_bbox, od_score, od_class_id in zip(
            class_id_list,
            score_list,
            od_bboxes,
            od_scores,
            od_class_ids,
    ):
        x1, y1 = int(od_bbox[0]), int(od_bbox[1])
        x2, y2 = int(od_bbox[2]), int(od_bbox[3])

        if od_score_th > od_score:
            continue

        color = get_color(od_class_id)

        # バウンディングボックス
        debug_image = cv2.rectangle(
            debug_image,
            (x1, y1),
            (x2, y2),
            color,
            thickness=thickness,
        )

        # Object Detection：クラスID、スコア
        score_text = '%.2f' % od_score
        od_class_name = get_class_name(od_class_id, od_class_names)
        text = '%s:%s(%s)' % (int(od_class_id), str(od_class_name), score_text)
        debug_image = cv2.putText(
            debug_image,
            'Detection(' + text + ')',
            (x1, y1 - 36),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=thickness,
        )

        # Classification：クラスID、スコア
        score_text = '%.2f' % score
        class_name = get_class_name(class_id, class_name_dict)
        text = '%s:%s(%s)' % (int(class_id), str(class_name), score_text)
        debug_image = cv2.putText(
            debug_image,
            'Classification(' + text + ')',
            (x1, y1 - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            thickness=thickness,
        )

    return debug_image


def draw_semantic_segmentation_info(
    image,
    score_th,
    class_num,
    segmentation_map,
):
    debug_image = copy.deepcopy(image)

    segmentation_map = np.where(segmentation_map > score_th, 0, 1)

    # color map list
    color_map = get_color_map_list(class_num)

    for index, mask in enumerate(segmentation_map):
        bg_image = np.zeros(image.shape, dtype=np.uint8)
        bg_image[:] = (color_map[index * 3 + 0], color_map[index * 3 + 1],
                       color_map[index * 3 + 2])

        mask = np.stack((mask, ) * 3, axis=-1).astype('uint8')

        mask_image = np.where(mask, debug_image, bg_image)
        debug_image = cv2.addWeighted(debug_image, 0.5, mask_image, 0.5, 1.0)

    return debug_image


def draw_pose_estimation_info(model_name, image, results_list, score_th):
    debug_image = copy.deepcopy(image)

    move_net_nodes = [
        'MoveNet(SinglePose Lightning)',
        'MoveNet(SinglePose Thunder)',
        'MoveNet(MulitPose Lightning)',
    ]
    mediapipe_hands_nodes = [
        'MediaPipe Hands(Complexity0)',
        'MediaPipe Hands(Complexity1)',
    ]
    mediapipe_pose_nodes = [
        'MediaPipe Pose(Complexity0)',
        'MediaPipe Pose(Complexity1)',
        'MediaPipe Pose(Complexity2)',
    ]

    if model_name in move_net_nodes:
        debug_image = draw_movenet_info(debug_image, results_list, score_th)
    elif model_name in mediapipe_hands_nodes:
        debug_image = draw_mediapipe_hands_info(debug_image, results_list)
    elif model_name in mediapipe_pose_nodes:
        debug_image = draw_mediapipe_pose_info(
            debug_image,
            results_list,
            score_th,
        )

    return debug_image


def draw_mediapipe_hands_info(image, results_list):
    for results in results_list:
        # キーポイント
        for id in range(21):
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # 接続線
        # 親指
        cv2.line(image, results[2][:2], results[3][:2], (0, 255, 0), 2)
        cv2.line(image, results[3][:2], results[4][:2], (0, 255, 0), 2)

        # 人差指
        cv2.line(image, results[5][:2], results[6][:2], (0, 255, 0), 2)
        cv2.line(image, results[6][:2], results[7][:2], (0, 255, 0), 2)
        cv2.line(image, results[7][:2], results[8][:2], (0, 255, 0), 2)

        # 中指
        cv2.line(image, results[9][:2], results[10][:2], (0, 255, 0), 2)
        cv2.line(image, results[10][:2], results[11][:2], (0, 255, 0), 2)
        cv2.line(image, results[11][:2], results[12][:2], (0, 255, 0), 2)

        # 薬指
        cv2.line(image, results[13][:2], results[14][:2], (0, 255, 0), 2)
        cv2.line(image, results[14][:2], results[15][:2], (0, 255, 0), 2)
        cv2.line(image, results[15][:2], results[16][:2], (0, 255, 0), 2)

        # 小指
        cv2.line(image, results[17][:2], results[18][:2], (0, 255, 0), 2)
        cv2.line(image, results[18][:2], results[19][:2], (0, 255, 0), 2)
        cv2.line(image, results[19][:2], results[20][:2], (0, 255, 0), 2)

        # 手の平
        cv2.line(image, results[0][:2], results[1][:2], (0, 255, 0), 2)
        cv2.line(image, results[1][:2], results[2][:2], (0, 255, 0), 2)
        cv2.line(image, results[2][:2], results[5][:2], (0, 255, 0), 2)
        cv2.line(image, results[5][:2], results[9][:2], (0, 255, 0), 2)
        cv2.line(image, results[9][:2], results[13][:2], (0, 255, 0), 2)
        cv2.line(image, results[13][:2], results[17][:2], (0, 255, 0), 2)
        cv2.line(image, results[17][:2], results[0][:2], (0, 255, 0), 2)

        cx, cy = results['palm_moment']
        cv2.putText(image, results['label'], (cx - 20, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    return image


def draw_mediapipe_pose_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(33):
            landmark_x, landmark_y = results[id][0], results[id][1]
            visibility = results[id][3]

            if score_th > visibility:
                continue
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # 接続線
        # 右目
        if results[1][3] > score_th and results[2][3] > score_th:
            cv2.line(image, results[1][:2], results[2][:2], (0, 255, 0), 2)
        if results[2][3] > score_th and results[3][3] > score_th:
            cv2.line(image, results[2][:2], results[3][:2], (0, 255, 0), 2)

        # 左目
        if results[4][3] > score_th and results[5][3] > score_th:
            cv2.line(image, results[4][:2], results[5][:2], (0, 255, 0), 2)
        if results[5][3] > score_th and results[6][3] > score_th:
            cv2.line(image, results[5][:2], results[6][:2], (0, 255, 0), 2)

        # 口
        if results[9][3] > score_th and results[10][3] > score_th:
            cv2.line(image, results[9][:2], results[10][:2], (0, 255, 0), 2)

        # 肩
        if results[11][3] > score_th and results[12][3] > score_th:
            cv2.line(image, results[11][:2], results[12][:2], (0, 255, 0), 2)

        # 右腕
        if results[11][3] > score_th and results[13][3] > score_th:
            cv2.line(image, results[11][:2], results[13][:2], (0, 255, 0), 2)
        if results[13][3] > score_th and results[15][3] > score_th:
            cv2.line(image, results[13][:2], results[15][:2], (0, 255, 0), 2)

        # 左腕
        if results[12][3] > score_th and results[14][3] > score_th:
            cv2.line(image, results[12][:2], results[14][:2], (0, 255, 0), 2)
        if results[14][3] > score_th and results[16][3] > score_th:
            cv2.line(image, results[14][:2], results[16][:2], (0, 255, 0), 2)

        # 右手
        if results[15][3] > score_th and results[17][3] > score_th:
            cv2.line(image, results[15][:2], results[17][:2], (0, 255, 0), 2)
        if results[17][3] > score_th and results[19][3] > score_th:
            cv2.line(image, results[17][:2], results[19][:2], (0, 255, 0), 2)
        if results[19][3] > score_th and results[21][3] > score_th:
            cv2.line(image, results[19][:2], results[21][:2], (0, 255, 0), 2)
        if results[21][3] > score_th and results[15][3] > score_th:
            cv2.line(image, results[21][:2], results[15][:2], (0, 255, 0), 2)

        # 左手
        if results[16][3] > score_th and results[18][3] > score_th:
            cv2.line(image, results[16][:2], results[18][:2], (0, 255, 0), 2)
        if results[18][3] > score_th and results[20][3] > score_th:
            cv2.line(image, results[18][:2], results[20][:2], (0, 255, 0), 2)
        if results[20][3] > score_th and results[22][3] > score_th:
            cv2.line(image, results[20][:2], results[22][:2], (0, 255, 0), 2)
        if results[22][3] > score_th and results[16][3] > score_th:
            cv2.line(image, results[22][:2], results[16][:2], (0, 255, 0), 2)

        # 胴体
        if results[11][3] > score_th and results[23][3] > score_th:
            cv2.line(image, results[11][:2], results[23][:2], (0, 255, 0), 2)
        if results[12][3] > score_th and results[24][3] > score_th:
            cv2.line(image, results[12][:2], results[24][:2], (0, 255, 0), 2)
        if results[23][3] > score_th and results[24][3] > score_th:
            cv2.line(image, results[23][:2], results[24][:2], (0, 255, 0), 2)

        # 右足
        if results[23][3] > score_th and results[25][3] > score_th:
            cv2.line(image, results[23][:2], results[25][:2], (0, 255, 0), 2)
        if results[25][3] > score_th and results[27][3] > score_th:
            cv2.line(image, results[25][:2], results[27][:2], (0, 255, 0), 2)
        if results[27][3] > score_th and results[29][3] > score_th:
            cv2.line(image, results[27][:2], results[29][:2], (0, 255, 0), 2)
        if results[29][3] > score_th and results[31][3] > score_th:
            cv2.line(image, results[29][:2], results[31][:2], (0, 255, 0), 2)

        # 左足
        if results[24][3] > score_th and results[26][3] > score_th:
            cv2.line(image, results[24][:2], results[26][:2], (0, 255, 0), 2)
        if results[26][3] > score_th and results[28][3] > score_th:
            cv2.line(image, results[26][:2], results[28][:2], (0, 255, 0), 2)
        if results[28][3] > score_th and results[30][3] > score_th:
            cv2.line(image, results[28][:2], results[30][:2], (0, 255, 0), 2)
        if results[30][3] > score_th and results[32][3] > score_th:
            cv2.line(image, results[30][:2], results[32][:2], (0, 255, 0), 2)
    return image


def draw_movenet_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(17):
            landmark_x, landmark_y = results[id][0], results[id][1]
            visibility = results[id][2]

            if score_th > visibility:
                continue
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # Line：鼻 → 左目
        if results[0][2] > score_th and results[1][2] > score_th:
            cv2.line(image, results[0][:2], results[1][:2], (0, 255, 0), 2)
        # Line：鼻 → 右目
        if results[0][2] > score_th and results[2][2] > score_th:
            cv2.line(image, results[0][:2], results[2][:2], (0, 255, 0), 2)
        # Line：左目 → 左耳
        if results[1][2] > score_th and results[3][2] > score_th:
            cv2.line(image, results[1][:2], results[3][:2], (0, 255, 0), 2)
        # Line：右目 → 右耳
        if results[2][2] > score_th and results[4][2] > score_th:
            cv2.line(image, results[2][:2], results[4][:2], (0, 255, 0), 2)
        # Line：左肩 → 右肩
        if results[5][2] > score_th and results[6][2] > score_th:
            cv2.line(image, results[5][:2], results[6][:2], (0, 255, 0), 2)
        # Line：左肩 → 左肘
        if results[5][2] > score_th and results[7][2] > score_th:
            cv2.line(image, results[5][:2], results[7][:2], (0, 255, 0), 2)
        # Line：左肘 → 左手首
        if results[7][2] > score_th and results[9][2] > score_th:
            cv2.line(image, results[7][:2], results[9][:2], (0, 255, 0), 2)
        # Line：右肩 → 右肘
        if results[6][2] > score_th and results[8][2] > score_th:
            cv2.line(image, results[6][:2], results[8][:2], (0, 255, 0), 2)
        # Line：右肘 → 右手首
        if results[8][2] > score_th and results[10][2] > score_th:
            cv2.line(image, results[8][:2], results[10][:2], (0, 255, 0), 2)
        # Line：左股関節 → 右股関節
        if results[11][2] > score_th and results[12][2] > score_th:
            cv2.line(image, results[11][:2], results[12][:2], (0, 255, 0), 2)
        # Line：左肩 → 左股関節
        if results[5][2] > score_th and results[11][2] > score_th:
            cv2.line(image, results[5][:2], results[11][:2], (0, 255, 0), 2)
        # Line：左股関節 → 左ひざ
        if results[11][2] > score_th and results[13][2] > score_th:
            cv2.line(image, results[11][:2], results[13][:2], (0, 255, 0), 2)
        # Line：左ひざ → 左足首
        if results[13][2] > score_th and results[15][2] > score_th:
            cv2.line(image, results[13][:2], results[15][:2], (0, 255, 0), 2)
        # Line：右肩 → 右股関節
        if results[6][2] > score_th and results[12][2] > score_th:
            cv2.line(image, results[6][:2], results[12][:2], (0, 255, 0), 2)
        # Line：右股関節 → 右ひざ
        if results[12][2] > score_th and results[14][2] > score_th:
            cv2.line(image, results[12][:2], results[14][:2], (0, 255, 0), 2)
        # Line：右ひざ → 右足首
        if results[14][2] > score_th and results[16][2] > score_th:
            cv2.line(image, results[14][:2], results[16][:2], (0, 255, 0), 2)

        bbox = results.get('bbox', None)
        if bbox is not None:
            if bbox[4] > score_th:
                image = cv2.rectangle(
                    image,
                    (bbox[0], bbox[1]),
                    (bbox[2], bbox[3]),
                    (0, 255, 0),
                    thickness=2,
                )

    return image


def draw_face_detection_info(model_name, image, results_list, score_th):
    debug_image = copy.deepcopy(image)

    if model_name == 'MediaPipe FaceDetection(~2m)' or \
            model_name == 'MediaPipe FaceDetection(~5m)':
        debug_image = draw_mediapipe_face_detection_info(
            debug_image,
            results_list,
            score_th,
        )
    elif model_name == 'MediaPipe FaceMesh' or \
            model_name == 'MediaPipe FaceMesh(Refine Landmark)':
        debug_image = draw_mediapipe_facemesh_info(
            debug_image,
            results_list,
            score_th,
        )
    elif model_name == 'YuNet':
        debug_image = draw_yunet_info(
            debug_image,
            results_list,
            score_th,
        )

    return debug_image


def draw_mediapipe_face_detection_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(6):
            if score_th > results[id][2]:
                continue
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # バウンディングボックス
        bbox = results.get('bbox', None)
        if bbox is not None:
            image = cv2.rectangle(
                image,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                (0, 255, 0),
                thickness=2,
            )

    return image





def draw_yunet_info(image, results_list, score_th):
    for results in results_list:
        # キーポイント
        for id in range(5):
            if score_th > results[id][2]:
                continue
            landmark_x, landmark_y = results[id][0], results[id][1]
            cv2.circle(image, (landmark_x, landmark_y), 5, (0, 255, 0), -1)

        # バウンディングボックス
        bbox = results.get('bbox', None)
        if bbox is not None:
            image = cv2.rectangle(
                image,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                (0, 255, 0),
                thickness=2,
            )

    return image


def draw_multi_object_tracking_info(
    image,
    track_ids,
    bboxes,
    scores,
    class_ids,
    class_names,
    track_id_dict,
):
    # Calculate font scale based on image height
    # Reference height: 720px, base font scale: 0.5
    # This makes font size proportional to image size
    image_height = image.shape[0]
    font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))
    
    # Calculate vertical offset and thickness based on font scale
    vertical_offset_1 = int(36 * (font_scale / 0.5))
    vertical_offset_2 = int(12 * (font_scale / 0.5))
    thickness = max(1, int(2 * (font_scale / 0.5)))
    
    # Thicker bounding box
    bbox_thickness = 4
    
    for id, bbox, score, class_id in zip(track_ids, bboxes, scores, class_ids):
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

        color = get_color(track_id_dict[id])

        # バウンディングボックス - Thicker rectangles
        image = cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            color,
            thickness=bbox_thickness,
        )

        # トラックID、スコア - with filled background
        score_text = '%.2f' % score
        tid_text = 'TID:%s(%s)' % (str(int(track_id_dict[id])), score_text)
        
        # Get text size for TID
        (tid_width, tid_height), tid_baseline = cv2.getTextSize(
            tid_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )
        
        # Draw filled background rectangle for TID with bounds checking
        tid_bg_y1 = max(0, y1 - vertical_offset_1 - tid_height - tid_baseline)
        tid_bg_y2 = max(0, y1 - vertical_offset_1 + tid_baseline)
        cv2.rectangle(
            image,
            (x1, tid_bg_y1),
            (x1 + tid_width, tid_bg_y2),
            color,
            thickness=-1,  # Filled rectangle
        )
        
        # Draw TID text with contrasting color (white)
        image = cv2.putText(
            image,
            tid_text,
            (x1, y1 - vertical_offset_1),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),  # White text for visibility
            thickness=thickness,
        )

        # クラスID - with filled background
        class_name = get_class_name(class_id, class_names)
        cid_text = 'CID:%s(%s)' % (str(int(class_id)), class_name)
        
        # Get text size for CID
        (cid_width, cid_height), cid_baseline = cv2.getTextSize(
            cid_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )
        
        # Draw filled background rectangle for CID with bounds checking
        cid_bg_y1 = max(0, y1 - vertical_offset_2 - cid_height - cid_baseline)
        cid_bg_y2 = max(0, y1 - vertical_offset_2 + cid_baseline)
        cv2.rectangle(
            image,
            (x1, cid_bg_y1),
            (x1 + cid_width, cid_bg_y2),
            color,
            thickness=-1,  # Filled rectangle
        )
        
        # Draw CID text with contrasting color (white)
        image = cv2.putText(
            image,
            cid_text,
            (x1, y1 - vertical_offset_2),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),  # White text for visibility
            thickness=thickness,
        )

    return image


