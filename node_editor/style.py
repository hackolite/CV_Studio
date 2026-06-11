INPUT = [
    "WebCam", "YoutubeLive",
    "Video", "YouTubeInput", "RTSP", "HLS", "VideoSetFramePos"
]
PROCESS = [
    "Resize", "Crop", "Zoom", "Grayscale", "ApplyColorMap", "Contrast",
    "Flip", "Brightness", "EqualizeHist", "CLAHE", "GammaCorrection",
    "OmnidirectionalViewer", "Blur", "Canny", "SimpleFilter",
    "Threshold", "ImageAlphaBlend", "BilateralFilter", "Morphology",
    "UnsharpMask", "NLMDenoise", "ColorSpace", "AdaptiveThreshold",
    "KernelSharpen", "IlluminationCorrect"
]
MODEL = [
    "LLIE", "Classification", "PoseEstimation", "ObjectDetection",
    "MonocularDepthEstimation", "SemanticSegmentation", "FaceDetection"
]
AUDIO_PROCESS = [
    "Spectrogram"
]
AUDIO_MODEL = ["AudioClassification"]
STATS = []
TRIGGER = ["Count", "OnOffSwitch"]
ROUTER = ["SimpleRouter"]
ACTION = []
VIDEO = ["ImageConcat", "VideoWriter", "ScreenCapture", "DynamicPlay"]
TRACKING = ["MultiObjectTracking", "ReId"]
OVERLAY = ["DrawInformation", "PutText"]
VIZ = ["Heatmap", "ObjChart", "Visual", "Map", "WordCloud"]
TIMESERIES = ["PositionPrediction"]
NLP_MODEL = ["TinyBertVigilance"]
SYSTEM = ["SyncQueue", "Scan", "SystemResource", "Sizing", "Settings"]
MAP    = ["CopernicusMap"]


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
        "style": [(255, 218, 185, 255)]  # peach puff pastel
    },
    "AudioProcess": {
        "names": AUDIO_PROCESS,
        "style": [(176, 224, 230, 255)]  # powder blue pastel
    },
    "AudioModel": {
        "names": AUDIO_MODEL,
        "style": [(255, 192, 203, 255)]  # pink pastel
    },
    "DataProcess": {
        "names": STATS,
        "style": [(173, 216, 230, 255)]  # light blue pastel (unchanged)
    },
    "DataModel": {
        "names": TIMESERIES,
        "style": [(255, 222, 243, 255)]  # very soft pastel pink
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
    "Overlay": {
        "names": OVERLAY,
        "style": [(245, 245, 245, 255)]  # very light gray (almost white)
    },
    "Tracking": {
        "names": TRACKING,
        "style": [(173, 216, 230, 255)]  # bleu pastel
    },
    "Video": {
        "names": VIDEO,
        "style": [(193, 255, 193, 255)]  # very light green pastel
    },
    "Visual": {
        "names": VIZ,
        "style": [(255, 182, 193, 255)]  # rose clair (light pink)
    },
    "NLPModel": {
        "names": NLP_MODEL,
        "style": [(200, 230, 255, 255)]  # light sky blue pastel
    },
    "System": {
        "names": SYSTEM,
        "style": [(192, 192, 192, 255)]  # silver gray pastel
    },
    "Map": {
        "names": MAP,
        "style": [(135, 206, 235, 255)]  # sky blue pastel
    }
}

