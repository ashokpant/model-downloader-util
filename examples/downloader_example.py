"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from modeldownloaderutil.downloader import get_model

if __name__ == '__main__':
    # print(get_model("~/.treeleaf-models/model_4_kps.onnx"))
    # print(get_model("https://github.com/onnx/models/raw/refs/heads/main/validated/vision/object_detection_segmentation/tiny-yolov2/model/tinyyolov2-7.onnx"))
    # get_model("s3://treeleaf-models/model_4_kps.onnx")
    # get_model("minio://treeleaf-models/model_4_kps.onnx")
    get_model("rustfs://treeleaf-models/model_4_kps.onnx")
    # get_model("gs://treeleaf-models/model_4_kps.onnx")
    # print(get_model("git+https://github.com/treeleaf-models.git#model_4_kps.onnx.zip"))
