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
        "style": [(255, 255, 153, 255)]  # jaune pastel doux
    },
    "VisionProcess": {
        "names": PROCESS,
        "style": [(144, 238, 144, 255)]  # vert pastel
    },
    "VisionModel": {
        "names": MODEL,
        "style": [(255, 218, 185, 255)]  # pêche pastel (peach puff)
    },
    "Stats": {
        "names": STATS,
        "style": [(173, 216, 230, 255)]  # bleu clair pastel (inchangé)
    },
    "Trigger": {
        "names": TRIGGER,
        "style": [(221, 160, 221, 255)]  # violet clair (plum pastel)
    },
    "Router": {
        "names": ROUTER,
        "style": [(216, 191, 216, 255)]  # lavande pastel
    },
    "Action": {
        "names": ACTION,
        "style": [(255, 204, 153, 255)]  # orange pastel doux
    },
    "Video": {
        "names": VIDEO,
        "style": [(193, 255, 193, 255)]  # vert très clair pastel
    },
    "Tracking": {
        "names": TRACKING,
        "style": [(173, 216, 230, 255)]  # bleu pastel
    },
    "Overlay": {
        "names": OVERLAY,
        "style": [(245, 245, 245, 255)]  # gris très clair (presque blanc)
    },
    "Viz": {
        "names": VIZ,
        "style": [(255, 182, 193, 255)]  # rose clair (light pink)
    },
    "Timeseries": {
        "names": TIMESERIES,
        "style": [(255, 222, 243, 255)]  # rose pastel très tendre
    }
}

