"""
-- Created by: Ashok Kumar Pant
-- Email: asokpant@gmail.com
-- Created on: 04/06/2026
"""
from modeldownloaderutil import download_model

if __name__ == "__main__":
    print(download_model("rustfs://treeleaf/models/model.onnx"))
    # print(download_model("git+https://github.com/treeleaftech/models/abc.zip"))
    # print(download_model("git://https://github.com/treeleaftech/models/abc.onnx"))
