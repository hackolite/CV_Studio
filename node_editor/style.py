INPUT = [
    "WebCam", "YoutubeLive", "Image", "IntValue", "FloatValue",
    "Video", "YouTubeInput", "RTSP", "VideoSetFramePos"
]
PROCESS = [
    "Resize", "Crop", "Resize", "Grayscale", "ApplyColorMap", "Contrast",
    "Flip", "Brightness", "EqualizeHist", "GammaCorrection",
    "OmnidirectionalViewer", "Blur", "Canny", "SimpleFilter",
    "Threshold", "ImageAlphaBlend"
]
MODEL = [
    "LLIE", "Classification", "PoseEstimation", "ObjectDetection",
    "MonocularDepthEstimation", "SemanticSegmentation", "FaceDetection"
]
STATS = []
TRIGGER = ["Count", "OnOffSwitch"]
ROUTER = []
ACTION = []
VIDEO = ["ImageConcat", "VideoWriter", "ScreenCapture"]
TRACKING = ["MultiObjectTracking"]
OVERLAY = ["DrawInformation", "PutText"]
VIZ = ["Heatmap"]
TIMESERIES = []



STYLE = {
    "Input": {
        "names": INPUT,
        "style": [(255, 255, 0, 255)]  # jaune
    },
    "VisionProcess": {
        "names": PROCESS,
        "style": [(0, 128, 0, 255)]  # vert plein
    },
    "VisionModel": {
        "names": MODEL,
        "style": [(255, 165, 0, 255)]  # tournesol (jaune doré)
    },
    "Stats": {
        "names": STATS,
        "style": [(173, 216, 230, 255)]  # bleu clair (light blue)
    },
    "Trigger": {
        "names": TRIGGER,
        "style": [(255, 0, 255, 255)]  # magenta
    },
    "Router": {
        "names": ROUTER,
        "style": [(128, 0, 128, 255)]  # violet
    },
    "Action": {
        "names": ACTION,
        "style": [(255, 165, 0, 255)]  # orange
    },
    "Video": {
        "names": VIDEO,
        "style": [(144, 238, 144, 255)]  # vert clair (light green)
    },
    "Tracking": {
        "names": TRACKING,
        "style": [(0, 0, 255, 255)]  # bleu plein
    },
    "Overlay": {
        "names": OVERLAY,
        "style": [(255, 255, 255, 255)]  # blanc
    },
    "Viz": {
        "names": VIZ,
        "style": [(255, 0, 0, 255)]  # rouge
    },
    "Timeseries": {
        "names": TIMESERIES,
        "style": [(255, 192, 203, 255)]  # rose (pink)
    }
}
