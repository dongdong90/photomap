"""
照片地图生成器
版本: v0.9.1
开发日期: 2024-03
开发者: dong, yi, flow, qwen, gemini, grok
版权所有 © 2024 照片地图项目组。保留所有权利。

本模块负责生成照片地图的HTML文件，包括：
- 地图初始化
- 照片标记添加
- 弹窗样式设置
- 地图交互功能
- 智能过滤：只显示有GPS坐标的照片

开源引用说明：
- Leaflet.js (https://leafletjs.com) - 用于地图展示，遵循 BSD-2-Clause 许可
- OpenStreetMap (https://www.openstreetmap.org) - 地图数据来源，遵循 ODbL 许可
"""

import os
import base64
from jinja2 import Template
from config import MAP_HTML_NAME
import logging
from datetime import datetime
import sys
import pkg_resources

def image_to_base64(image_path):
    """
    将图片文件转换为Base64编码
    
    参数:
        image_path (str): 图片文件路径
    
    返回:
        str: Base64编码的图片数据，失败则返回None
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            # 根据文件扩展名确定MIME类型
            if image_path.lower().endswith('.png'):
                return f"data:image/png;base64,{encoded_string}"
            elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
                return f"data:image/jpeg;base64,{encoded_string}"
            else:
                return f"data:image/png;base64,{encoded_string}"  # 默认使用PNG
    except Exception as e:
        logging.error(f"转换图片 {image_path} 为Base64失败: {str(e)}")
        return None

def generate_map_html(photo_data, base_dir, html_filename="photo_map.html"):
    """
    生成包含照片位置的HTML地图文件
    
    参数:
        photo_data (list): 包含照片信息的列表，每个元素为字典，包含经纬度等信息
        base_dir (str): 生成HTML文件的保存目录
        html_filename (str): 生成的HTML文件名，默认为"photo_map.html"
    
    返回:
        str: 生成的HTML文件路径，失败则返回None
    """
    # 检查输入数据
    if not photo_data:
        logging.error("photo_data为空，无法生成地图")
        return None

    # 按拍摄时间排序照片，未知时间的放最后
    photo_data = sorted(photo_data, key=lambda x: x.get('shoot_time') or datetime.max)

    # 计算照片坐标的边界，过滤掉没有GPS信息的照片（用于计算地图边界）
    # 更严格的过滤，确保坐标是有效的数字，并排除坐标为0的照片
    valid_photos = [p for p in photo_data if p["latitude"] is not None and p["longitude"] is not None and isinstance(p["latitude"], (int, float)) and isinstance(p["longitude"], (int, float)) and not (p["latitude"] == 0 and p["longitude"] == 0)]
    
    # 使用所有照片数据（包括没有GPS信息的照片）来渲染地图标记
    # 但对于没有GPS信息的照片，将在地图中心位置显示
    all_photos_for_rendering = photo_data
    
    # 如果没有有效的GPS坐标数据，使用默认坐标范围（北京中心）
    if not valid_photos:
        logging.warning("没有有效的GPS坐标数据，使用默认地图中心")
        min_lat, max_lat = 39.9042, 39.9042
        min_lon, max_lon = 116.4074, 116.4074
    else:
        latitudes = [p["latitude"] for p in valid_photos]
        longitudes = [p["longitude"] for p in valid_photos]
        min_lat = min(latitudes)
        max_lat = max(latitudes)
        min_lon = min(longitudes)
        max_lon = max(longitudes)

    # 将二维码图片转换为Base64编码
    wechat_qrcode_base64 = image_to_base64(os.path.join(base_dir, "wechat_qrcode.png"))
    alipay_qrcode_base64 = image_to_base64(os.path.join(base_dir, "alipay_qrcode.png"))
    
    # 如果转换失败，使用默认的相对路径
    if not wechat_qrcode_base64:
        wechat_qrcode_base64 = "wechat_qrcode.png"
        logging.warning("微信二维码图片转换为Base64失败，使用相对路径")
        
    if not alipay_qrcode_base64:
        alipay_qrcode_base64 = "alipay_qrcode.png"
        logging.warning("支付宝二维码图片转换为Base64失败，使用相对路径")

    # HTML 模板字符串
    template_str = r"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>照片地图</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.css" />
        <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.4.1/dist/MarkerCluster.Default.css" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/css/lightgallery-bundle.min.css" />
        <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
        <script src="https://unpkg.com/leaflet.markercluster@1.4.1/dist/leaflet.markercluster.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/lightgallery.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/plugins/pager/lg-pager.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/plugins/zoom/lg-zoom.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/plugins/fullscreen/lg-fullscreen.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/plugins/thumbnail/lg-thumbnail.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/plugins/rotate/lg-rotate.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lightgallery/2.7.2/plugins/hash/lg-hash.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/js/all.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
        <style>
            html, body { 
                height: 100%; 
                margin: 0; 
                padding: 0; 
                font-family: "等线", "Microsoft YaHei", sans-serif;
                font-weight: bold;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                color: #333;
            }
            #map { 
                height: 100vh; 
                width: 100%; 
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }
            .marker-cluster {
                position: absolute;
                top: -10px;
                right: -10px;
                width: 24px;
                height: 24px;
                background: linear-gradient(45deg, #ff7f50, #ff4e50);
                border-radius: 50%;
                text-align: center;
                line-height: 24px;
                color: white;
                font-weight: bold;
                box-shadow: 0 3px 6px rgba(0,0,0,0.16);
                border: 2px solid white;
            }
            .custom-marker {
                transition: all 0.3s ease;
                transform: translateY(0);
            }
            .custom-marker:hover {
                transform: translateY(-5px);
                filter: brightness(1.1);
            }
            .custom-marker img {
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                border: 2px solid white;
            }
            .about-dialog {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 25px;
                border: none;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                z-index: 1001;
                width: 350px;
                text-align: center;
                opacity: 0;
                transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
                font-family: "等线", "Microsoft YaHei", sans-serif;
                font-weight: bold;
                border-radius: 16px;
            }
            .about-link {
                margin-top: 16px;
                display: inline-block;
                padding: 10px 18px;
                background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
                color: white;
                text-decoration: none;
                border-radius: 30px;
                font-weight: bold;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                box-shadow: 0 4px 10px rgba(79, 172, 254, 0.4);
            }
            .about-link:hover {
                transform: translateY(-2px);
                box-shadow: 0 7px 14px rgba(79, 172, 254, 0.5);
            }
            .about-dialog .close-btn {
                position: absolute;
                top: 15px;
                right: 15px;
                font-size: 24px;
                cursor: pointer;
                width: 30px;
                height: 30px;
                line-height: 30px;
                text-align: center;
                border-radius: 50%;
                background: #f2f3f5;
                transition: all 0.3s ease;
            }
            .about-dialog .close-btn:hover {
                background: #e5e7eb;
                transform: rotate(90deg);
            }
            .custom-cluster-pop-up {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;
                border: none;
                box-shadow: 0 15px 40px rgba(0,0,0,0.2);
                z-index: 1000;
                max-width: 92vw;
                max-height: 92vh;
                overflow: hidden;
                opacity: 0;
                transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
                font-family: "等线", "Microsoft YaHei", sans-serif;
                font-weight: bold;
                border-radius: 18px;
            }
            .closebtn {
                position: absolute;
                top: 15px;
                right: 15px;
                font-size: 24px;
                cursor: pointer;
                width: 36px;
                height: 36px;
                line-height: 36px;
                text-align: center;
                border-radius: 50%;
                background: #f2f3f5;
                transition: all 0.3s ease;
                z-index: 2;
            }
            .closebtn:hover {
                background: #e5e7eb;
                transform: rotate(90deg);
            }
            /* LightGallery 自定义样式 */
            .lg-backdrop {
                background-color: rgba(0, 0, 0, 0.9);
            }
            /* Center the image vertically */
            .lg-inner {
                display: flex;
                flex-direction: column;
                justify-content: center;
                height: 100%;
                padding-top: 0;
                margin-top: -1.35%;  /* Move image upward */
            }
            .lg-img-wrap {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100%;
            }
            /* Style for the date label below the image */
            .photo-date-bottom {
                text-align: center;
                background: linear-gradient(to right, #ff416c, #ff4b2b);
                color: white;
                padding: 8px 16px;
                border-radius: 30px;
                font-family: '等线', 'Microsoft YaHei', sans-serif;
                font-weight: bold;
                font-size: 18px;
                margin-top: 15px;
                display: inline-block;
                box-shadow: 0 4px 12px rgba(255, 65, 108, 0.4);
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% {
                    box-shadow: 0 0 0 0 rgba(255, 65, 108, 0.7);
                }
                70% {
                    box-shadow: 0 0 0 10px rgba(255, 65, 108, 0);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(255, 65, 108, 0);
                }
            }
            .lg-sub-html {
                background-color: rgba(0, 0, 0, 0.5);
                bottom: 0;
                color: #fff;
                font-size: 16px;
                left: 0;
                padding: 15px 40px;
                position: fixed;
                right: 0;
                text-align: center;
                z-index: 1080;
                backdrop-filter: blur(8px);
            }
            .lg-toolbar .lg-icon,
            .lg-actions .lg-next, 
            .lg-actions .lg-prev {
                background: linear-gradient(to right, rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.4));
                border-radius: 50%;
                color: white;
                cursor: pointer;
                display: block;
                font-size: 24px;
                margin-top: -10px;
                padding: 12px 14px;
                position: absolute;
                top: 50%;
                z-index: 1080;
                border: none;
                outline: none;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
            }
            .lg-toolbar .lg-icon:hover,
            .lg-actions .lg-next:hover, 
            .lg-actions .lg-prev:hover {
                background: linear-gradient(to right, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.6));
                transform: scale(1.1);
            }
            /* Enhance the lightgallery image container with rounded corners and shadow */
            .lg-image {
                border-radius: 8px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            }
            
            /* 新增旋转和信息按钮样式 */
            .lg-rotate-left, .lg-rotate-right, .lg-info-btn {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: linear-gradient(to right, rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.4));
                margin: 0 8px;  /* 增加按钮之间的间距 */
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;  /* 添加相对定位 */
                z-index: 1080;  /* 确保按钮在最上层 */
            }
            
            .lg-rotate-left {
                margin-right: 12px;  /* 为旋转按钮添加额外的右边距 */
            }
            
            .lg-info-btn {
                margin-left: 12px;  /* 为信息按钮添加额外的左边距 */
            }
            
            .lg-rotate-left:hover, .lg-rotate-right:hover, .lg-info-btn:hover {
                background: linear-gradient(to right, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.6));
                transform: scale(1.1);
            }
            
            /* 信息面板样式 */
            .lg-info-panel {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                width: 100%;
                background: rgba(0, 0, 0, 0.85);
                color: white;
                padding: 20px;
                box-sizing: border-box;
                transform: translateY(100%);
                transition: transform 0.4s ease, opacity 0.4s ease;
                z-index: 1080;
                opacity: 0;
                display: none;
                backdrop-filter: blur(8px);
                box-shadow: 0 -5px 15px rgba(0, 0, 0, 0.2);
                max-height: 50%;
                overflow-y: auto;
            }
            
            .lg-info-panel.show {
                transform: translateY(0);
                opacity: 1;
            }
            
            .lg-info-panel-inner {
                max-width: 800px;
                margin: 0 auto;
                font-family: "等线", "Microsoft YaHei", sans-serif;
            }
            
            .lg-info-panel h3 {
                margin-top: 0;
                margin-bottom: 20px;
                color: #ff416c;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                padding-bottom: 10px;
                font-size: 22px;
                text-align: center;
                font-family: "等线", "Microsoft YaHei", sans-serif;
            }
            
            .lg-info-panel table {
                width: 100%;
                border-collapse: collapse;
                border: none;
            }
            
            .lg-info-panel table td {
                padding: 10px 0;
                vertical-align: top;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .lg-info-panel table td:first-child {
                width: 30%;
                color: rgba(255, 255, 255, 0.7);
                font-weight: bold;
            }
            
            /* 鹰眼导航样式 */
            .lg-eagle-eye {
                position: absolute;
                bottom: 20px;
                right: 20px;
                width: 150px;
                height: 150px;
                border: 2px solid white;
                background-color: black;
                opacity: 0.7;
                overflow: hidden;
                transition: opacity 0.3s;
                z-index: 1090;
            }
            
            .lg-eagle-eye:hover {
                opacity: 1;
            }

            .lg-eagle-eye-img {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: contain;
            }
            
            .lg-eagle-eye-viewport {
                position: absolute;
                border: 2px solid red;
                box-sizing: border-box;
                pointer-events: none;
            }
            
            /* 缩略图网格样式 */
            .thumbnails-grid {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                grid-template-rows: repeat(3, 1fr);
                gap: 16px; /* 保持网格间距 */
                padding: 20px; /* 保持内边距 */
                height: calc(100% - 10px); /* 调整高度以减少空白区域 */
                overflow: hidden;
                background-color: #f8f9fa;
                border-radius: 12px;
            }
            .thumbnails-grid img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
            }
            .thumbnails-grid img:hover {
                transform: translateY(-5px) scale(1.03);
                box-shadow: 0 10px 20px rgba(0,0,0,0.15);
            }
            .lg-toolbar .lg-close {
                font-size: 28px;
                padding: 14px;
                background: linear-gradient(to right, rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.4));
                border-radius: 50%;
                margin: 15px;
                position: absolute;
                right: 15px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }
            .lg-toolbar .lg-close:hover {
                background: linear-gradient(to right, rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.6));
                transform: rotate(90deg);
            }
            /* 分页按钮样式 */
            .pagination {
                padding: 15px 0;
                background: #f8f9fa;
                border-top: 1px solid #eee;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 8px;
            }
            .pagination button {
                padding: 8px 16px;
                border: none;
                background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
                color: white;
                cursor: pointer;
                border-radius: 30px;
                font-family: "等线", "Microsoft YaHei", sans-serif;
                font-weight: bold;
                transition: all 0.3s ease;
                box-shadow: 0 4px 10px rgba(79, 172, 254, 0.3);
            }
            .pagination button.active {
                background: linear-gradient(to right, #ff416c, #ff4b2b);
                color: white;
                box-shadow: 0 4px 10px rgba(255, 65, 108, 0.4);
                transform: scale(1.05);
            }
            .pagination button:hover:not(.active):not(:disabled) {
                transform: translateY(-3px);
                box-shadow: 0 7px 14px rgba(79, 172, 254, 0.4);
            }
            .pagination button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                background: #e0e0e0;
                color: #999;
                box-shadow: none;
            }
            /* 照片日期显示样式 */
            .photo-date {
                color: white !important;
                background: linear-gradient(to right, #ff416c, #ff4b2b);
                font-family: "等线", "Microsoft YaHei", sans-serif;
                font-weight: bold;
                font-size: 16px;
                padding: 8px 16px;
                border-radius: 30px;
                display: inline-block;
                box-shadow: 0 4px 12px rgba(255, 65, 108, 0.4);
            }
            /* About dialog styles */
            .about-dialog {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 600px;
                max-width: 90vw;
                max-height: 85vh;
                background: white;
                border-radius: 20px;
                box-shadow: 0 15px 40px rgba(0,0,0,0.2);
                opacity: 0;
                transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
                z-index: 1000;
                padding: 30px;
                text-align: left;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }
            .about-dialog .readme-content {
                line-height: 1.8;
                font-size: 16px;
                color: #444;
                padding: 10px 0;
            }
            .about-dialog h1, .about-dialog h2, .about-dialog h3 {
                color: #333;
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
            }
            .about-dialog h1 {
                font-size: 28px;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
                background: linear-gradient(to right, #ff416c, #ff4b2b);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .about-dialog h2 {
                font-size: 22px;
            }
            .about-dialog h3 {
                font-size: 18px;
            }
            .about-dialog p {
                margin-bottom: 16px;
            }
            .about-dialog ul, .about-dialog ol {
                margin-left: 24px;
                margin-bottom: 16px;
            }
            .about-dialog li {
                margin-bottom: 8px;
            }
            .about-dialog code {
                background: #f5f7fa;
                padding: 2px 5px;
                border-radius: 4px;
                font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
                font-size: 0.9em;
            }
            /* 隐藏原有工具栏 */
            .lg-toolbar.lg-group {
                opacity: 0 !important;
                pointer-events: none !important;
            }
            /* 垂直按钮容器样式 */
            .lg-vertical-buttons {
                position: fixed !important;
                top: 15px !important;
                right: 15px !important;
                display: flex !important;
                flex-direction: column !important;
                gap: 20px !important;
                z-index: 9999 !important;
            }
            /* 按钮通用样式 */
            .lg-btn {
                width: 46px !important;
                height: 46px !important;
                background: rgba(0, 0, 0, 0.5) !important;
                color: #fff !important;
                border: none !important;
                border-radius: 50% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                cursor: pointer !important;
                transition: all 0.3s !important;
                font-size: 18px !important;
                padding: 0 !important;
                margin: 0 !important;
                box-shadow: 0 3px 6px rgba(0, 0, 0, 0.16) !important;
            }
            /* 关闭按钮特殊样式 */
            .lg-close-btn {
                background: rgba(255, 0, 0, 0.7) !important;
            }
            /* 按钮悬停效果 */
            .lg-btn:hover {
                transform: scale(1.1) !important;
                background: rgba(0, 0, 0, 0.8) !important;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.25) !important;
            }
            /* 关闭按钮悬停效果 */
            .lg-close-btn:hover {
                background: rgba(255, 0, 0, 0.9) !important;
            }
            /* 图标调整 */
            .lg-btn i {
                font-size: 20px !important;
            }
            /* 信息面板样式 */
            .lg-info-panel {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                width: 100%;
                background: rgba(0, 0, 0, 0.85);
                color: white;
                padding: 20px;
                box-sizing: border-box;
                transform: translateY(100%);
                transition: transform 0.4s ease, opacity 0.4s ease;
                z-index: 1080;
                opacity: 0;
                display: none;
                backdrop-filter: blur(8px);
                box-shadow: 0 -5px 15px rgba(0, 0, 0, 0.2);
                max-height: 50%;
                overflow-y: auto;
            }
            .lg-info-panel.show {
                transform: translateY(0);
                opacity: 1;
            }
            .lg-info-panel-inner {
                max-width: 800px;
                margin: 0 auto;
                font-family: "等线", "Microsoft YaHei", sans-serif;
            }
            .lg-info-panel h3 {
                margin-top: 0;
                margin-bottom: 20px;
                color: #ff416c;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                padding-bottom: 10px;
                font-size: 22px;
                text-align: center;
                font-family: "等线", "Microsoft YaHei", sans-serif;
            }
            .lg-info-panel table {
                width: 100%;
                border-collapse: collapse;
                border: none;
            }
            .lg-info-panel table td {
                padding: 10px 0;
                vertical-align: top;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .lg-info-panel table td:first-child {
                width: 30%;
                color: rgba(255, 255, 255, 0.7);
                font-weight: bold;
            }
            /* 鹰眼导航窗口样式 */
            .lg-eagle-eye {
                position: absolute;
                bottom: 20px;
                right: 20px;
                width: 150px;
                height: 150px;
                border: 2px solid white;
                background-color: black;
                opacity: 0.7;
                overflow: hidden;
                transition: opacity 0.3s;
                z-index: 1090;
            }
            .lg-eagle-eye:hover {
                opacity: 1;
            }
            .lg-eagle-eye-img {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: contain;
            }
            .lg-eagle-eye-viewport {
                position: absolute;
                border: 2px solid red;
                box-sizing: border-box;
                pointer-events: none;
            }
            
            /* 捐款相关样式 */
            .donation-container {
                display: flex;
                justify-content: center;
                gap: 30px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            
            .donation-box {
                display: flex;
                flex-direction: column;
                align-items: center;
                background: #f9f9f9;
                border-radius: 16px;
                padding: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                transition: all 0.3s ease;
                width: 150px;
            }
            
            .donation-box:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.12);
            }
            
            .qrcode-image {
                width: 120px;
                height: 120px;
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 10px;
                border: 1px solid #eee;
                display: flex;
                align-items: center;
                justify-content: center;
                background-color: white;
            }
            
            .qrcode-image img {
                width: 100%;
                height: 100%;
                object-fit: contain;
                max-width: 120px;
                max-height: 120px;
            }
            
            .donation-label {
                font-size: 16px;
                font-weight: bold;
                margin: 0;
                background: linear-gradient(to right, #ff416c, #ff4b2b);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            .donation-note {
                background: rgba(79, 172, 254, 0.1);
                padding: 15px;
                border-radius: 12px;
                border-left: 4px solid #4facfe;
                margin: 15px 0;
                font-size: 15px;
            }
            
            .donation-list {
                margin: 10px 0 0 20px;
            }
            
            .donation-list li {
                margin-bottom: 5px;
                position: relative;
            }
            
            .donation-list li:before {
                content: '✓';
                color: #4facfe;
                position: absolute;
                left: -20px;
            }
            
            /* 广告相关样式 */
            .ad-container {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: rgba(255, 255, 255, 0.95);
                box-shadow: 0 -5px 20px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                transform: translateY(0);
                transition: transform 0.3s ease-in-out;
                font-family: "等线", "Microsoft YaHei", sans-serif;
            }
            
            .ad-wrapper {
                max-width: 900px;
                margin: 0 auto;
                padding: 0;
                display: flex;
                flex-direction: column;
            }
            
            .ad-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 15px;
                background: linear-gradient(to right, #f5f7fa, #eef2f7);
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            }
            
            .ad-header span {
                font-size: 12px;
                color: #666;
                font-weight: bold;
            }
            
            .ad-close-btn {
                background: none;
                border: none;
                color: #666;
                font-size: 18px;
                cursor: pointer;
                width: 24px;
                height: 24px;
                line-height: 22px;
                text-align: center;
                border-radius: 50%;
                transition: all 0.3s ease;
            }
            
            .ad-close-btn:hover {
                background: rgba(0, 0, 0, 0.1);
                transform: rotate(90deg);
            }
            
            .ad-content {
                padding: 15px;
                display: flex;
                justify-content: center;
            }
            
            .ad-placeholder {
                display: flex;
                width: 100%;
                max-width: 800px;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(0, 0, 0, 0.08);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .ad-placeholder:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            }
            
            .ad-placeholder-text {
                flex: 2;
                padding: 20px;
            }
            
            .ad-placeholder-text h3 {
                margin-top: 0;
                margin-bottom: 10px;
                font-size: 20px;
                background: linear-gradient(to right, #4facfe 0%, #00f2fe 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            .ad-placeholder-text p {
                margin: 10px 0;
                color: #444;
            }
            
            .ad-placeholder-text ul {
                margin: 10px 0 15px 20px;
                padding: 0;
                color: #555;
            }
            
            .ad-placeholder-text li {
                margin-bottom: 5px;
                position: relative;
                list-style: none;
            }
            
            .ad-placeholder-text li:before {
                content: '✓';
                color: #4facfe;
                position: absolute;
                left: -20px;
                font-weight: bold;
            }
            
            .ad-image {
                flex: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                padding: 10px;
            }
            
            .ad-image img {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                border-radius: 5px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            }
            
            .ad-cta-button {
                background: linear-gradient(to right, #ff416c, #ff4b2b);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 30px;
                font-family: "等线", "Microsoft YaHei", sans-serif;
                font-weight: bold;
                font-size: 15px;
                cursor: pointer;
                box-shadow: 0 4px 10px rgba(255, 65, 108, 0.3);
                transition: all 0.3s ease;
            }
            
            .ad-cta-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 7px 15px rgba(255, 65, 108, 0.4);
            }
            
            /* 响应式布局 */
            @media (max-width: 768px) {
                .ad-placeholder {
                    flex-direction: column-reverse;
                }
                
                .ad-image {
                    padding: 15px 15px 0 15px;
                }
                
                .ad-placeholder-text ul {
                    columns: 2;
                }
            }
            
            @media (max-width: 480px) {
                .ad-placeholder-text ul {
                    columns: 1;
                }
            }
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map', {
                maxZoom: 18
            });

            var streetLayer = L.tileLayer('https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}', {
                attribution: '© <a href="https://www.amap.com/">高德地图</a>'
            });

            var satelliteLayer = L.tileLayer('https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}', {
                attribution: '© <a href="https://www.amap.com/">高德卫星影像</a>'
            });

            streetLayer.addTo(map);  // 默认加载电子地图

            var baseLayers = {
                "电子地图": streetLayer,
                "卫星影像": satelliteLayer
            };
            var layerControl = L.control.layers(baseLayers).addTo(map);

           // 添加"关于"控件
            var AboutControl = L.Control.extend({
                options: { position: 'bottomright' },
                onAdd: function(map) {
                    var container = L.DomUtil.create('div', 'leaflet-control-about');
                    container.innerHTML = 'ℹ️';
                    container.title = '关于';
                    container.style.cursor = 'pointer';
                    
                    // 阻止事件冒泡
                    L.DomEvent.disableClickPropagation(container);
                    L.DomEvent.disableScrollPropagation(container);
                    
                    container.onclick = function(e) {
                        // 移除已存在的对话框
                        var existingDialog = document.querySelector('.about-dialog');
                        if (existingDialog) {
                            document.body.removeChild(existingDialog);
                        }
                        
                        var dialog = document.createElement('div');
                        dialog.className = 'about-dialog';
                        dialog.innerHTML = `
                            <span class="close-btn">×</span>
                            <div class="readme-content">
                                <h1>照片地图 - 基于地理位置的照片浏览工具</h1>
                                <h2>支持作者</h2>
                                <p>如果您觉得这个工具对您有所帮助，欢迎通过以下方式支持作者继续开发和维护：</p>
                                
                                <div class="donation-container">
                                    <div class="donation-box">
                                        <div class="qrcode-image">
                                            <!-- 微信二维码图片 -->
                                            <img src="{{ wechat_qrcode_base64 }}" alt="微信支付" title="微信支付" style="width: 120px; height: 120px; object-fit: contain;" />
                                        </div>
                                        <p class="donation-label">微信支付</p>
                                    </div>
                                    
                                    <div class="donation-box">
                                        <div class="qrcode-image">
                                            <!-- 支付宝二维码图片 -->
                                            <img src="{{ alipay_qrcode_base64 }}" alt="支付宝" title="支付宝" style="width: 120px; height: 120px; object-fit: contain;" />
                                        </div>
                                        <p class="donation-label">支付宝</p>
                    </div>
                </div>
                                
                                <p class="donation-note">
                                    您的每一笔捐款都将用于：
                                    <ul class="donation-list">
                                        <li>开发新功能和改进现有功能</li>
                                        <li>提高应用性能和用户体验</li>
                                        <li>功能维护和技术支持</li>
                                        <li>购买更多咖啡，让开发者熬夜加班 ☕</li>
                                    </ul>
                                </p>
                                <h2>功能介绍</h2>
                                <p>照片地图是一个能够根据照片的地理位置信息（经纬度）在地图上展示照片的工具。通过这个工具，您可以：</p>
                                <ul>
                                    <li>在地图上直观地查看照片拍摄位置</li>
                                    <li>根据拍摄地点浏览照片集</li>
                                    <li>查看照片的详细信息，包括拍摄日期</li>
                                    <li>以缩略图方式浏览同一地点的多张照片</li>
                                    <li>以全屏方式查看原始照片</li>
                                </ul>
                                
                                <h2>使用说明</h2>
                                <h3>地图导航</h3>
                                <ul>
                                    <li>放大/缩小：使用鼠标滚轮或地图右上角的 +/- 按钮</li>
                                    <li>移动地图：点击并拖动地图</li>
                                    <li>切换地图类型：点击右上角的图层控制按钮，选择"电子地图"或"卫星影像"</li>
                                </ul>
                                
                                <h3>照片查看</h3>
                                <ul>
                                    <li>查看照片位置：地图上的缩略图标记表示照片拍摄位置</li>
                                    <li>查看照片群组：数字标记表示该位置有多张照片，点击可查看</li>
                                    <li>浏览照片列表：点击照片群组时，会显示该位置的所有照片缩略图</li>
                                    <li>查看原图：点击任意缩略图可全屏查看原始照片</li>
                                    <li>翻页浏览：使用全屏模式下的左右箭头或缩略图列表底部的分页按钮</li>
                                </ul>
                                
                                <h2>技术特点</h2>
                                <ul>
                                    <li>自动聚合：相近位置的照片会自动聚合为照片群组</li>
                                    <li>日期排序：照片按拍摄日期排序，方便时间线浏览</li>
                                    <li>响应式布局：适配不同尺寸的屏幕</li>
                                    <li>优化的缩略图：保持照片原始比例，提供更好的预览体验</li>
                                    <li>美观的界面：渐变色、圆角、阴影等视觉元素提升用户体验</li>
                                </ul>
                                
                                
                                
                                <p>照片地图v0.9.1 by dong, yi, flow, qwen, gemini, grok </p>
                                <p>如有问题反馈或建议，欢迎发送邮件至 <a href="mailto:849371874@qq.com">849371874@qq.com</a></p>
                            </div>
                        `;
                        document.body.appendChild(dialog);
                        setTimeout(() => dialog.style.opacity = '1', 10);
                        dialog.querySelector('.close-btn').onclick = function() {
                            dialog.style.opacity = '0';
                            setTimeout(() => document.body.removeChild(dialog), 300);
                        };
                    };
                    return container;
                }
            });
            // 添加CSS样式（必须放在页面<head>中）
            var style = document.createElement('style');
            style.innerHTML = `
            .leaflet-control-about {
                font-size: 30px !important;
                width: 50px;
                height: 50px;
                line-height: 50px;
                background: white;
                border-radius: 50%;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                text-align: center;
                transition: all 0.3s ease;
            }

            .leaflet-control-about:hover {
                transform: scale(1.1) rotate(10deg);
                box-shadow: 0 8px 20px rgba(0,0,0,0.25);
            }

            .about-dialog .close-btn {
                position: absolute;
                top: 15px;
                right: 15px;
                font-size: 24px;
                cursor: pointer;
                width: 36px;
                height: 36px;
                line-height: 36px;
                text-align: center;
                border-radius: 50%;
                background: #f5f5f5;
                transition: all 0.3s ease;
                z-index: 1;
            }

            .about-dialog .close-btn:hover {
                background: #e5e7eb;
                transform: rotate(90deg);
            }
            `;
            document.head.appendChild(style);
            new AboutControl().addTo(map);

            // 延迟加载照片数据
            var markers = L.markerClusterGroup({
                spiderfyOnMaxZoom: false,  // 禁用默认的spiderfy行为
                zoomToBoundsOnClick: false,  // 禁用点击聚合标记时自动缩放地图
                iconCreateFunction: function(cluster) {
                    var childCount = cluster.getChildCount();
                    var markers = cluster.getAllChildMarkers();
                    var thumbnail = markers[0].options.thumbnail;
                    var width = markers[0].options.thumbWidth;
                    var height = markers[0].options.thumbHeight;
                    
                    // 计算缩放后的尺寸，最大尺寸为100px
                    var maxDim = Math.max(width, height);
                    var displayWidth = width > height ? 100 : Math.round(width * 100 / height);
                    var displayHeight = height > width ? 100 : Math.round(height * 100 / width);
                    
                    return L.divIcon({
                        html: '<div class="custom-marker"><img src="' + thumbnail + '" style="width: ' + displayWidth + 'px; height: ' + displayHeight + 'px;"><span class="marker-cluster">' + childCount + '</span></div>',
                        className: '',
                        iconSize: [displayWidth, displayHeight]
                    });
                }
            });

            var currentPopUp = null;
            var currentCustomPopUp = null;
            var currentClusterPhotos = [];

            // 监听簇点击事件
            markers.on('clusterclick', function(e) {
                var cluster = e.layer;
                var markers = cluster.getAllChildMarkers();
                var photos = markers.map(m => ({
                    photo_path: m.options.photoPath,
                    photo_date: m.options.photoDate,
                    shoot_time: m.options.shootTime || Number.MAX_VALUE,
                    thumb_path: m.options.thumbnail,
                    thumb_width: m.options.thumbWidth,
                    thumb_height: m.options.thumbHeight
                })).sort((a, b) => a.shoot_time - b.shoot_time);
                
                // 修改：不再判断地图缩放级别，直接显示照片列表
                showCustomPopUp(photos);
                
                e.originalEvent.preventDefault();
            });

                        {% for photo in photos %}
                {% if photo.latitude is not none and photo.longitude is not none %}
                {% set max_dim = photo.thumb_width if photo.thumb_width > photo.thumb_height else photo.thumb_height %}
                {% set display_width = 100 if photo.thumb_width > photo.thumb_height else (photo.thumb_width * 100 / photo.thumb_height)|int %}
                {% set display_height = 100 if photo.thumb_height > photo.thumb_width else (photo.thumb_height * 100 / photo.thumb_width)|int %}
                
                var marker = L.marker([{{ photo.latitude }}, {{ photo.longitude }}], {
                    icon: L.divIcon({
                        html: '<div class="custom-marker"><img src="{{ photo.thumbnail_path }}" style="width: {{ display_width }}px; height: {{ display_height }}px;"></div>',
                        className: '',
                        iconSize: [{{ display_width }}, {{ display_height }}]
                    }),
                    thumbnail: "{{ photo.thumbnail_path }}",
                    photoPath: "{{ photo.photo_path }}",
                    photoDate: "{{ photo.photo_date }}",
                    shootTime: {{ photo.shoot_time.timestamp() if photo.shoot_time else 'Number.MAX_VALUE' }},
                    thumbWidth: {{ photo.thumb_width }},
                    thumbHeight: {{ photo.thumb_height }}
                });
                {% else %}
                // 对于没有GPS信息的照片，在地图中心位置显示
                {% set max_dim = photo.thumb_width if photo.thumb_width > photo.thumb_height else photo.thumb_height %}
                {% set display_width = 100 if photo.thumb_width > photo.thumb_height else (photo.thumb_width * 100 / photo.thumb_height)|int %}
                {% set display_height = 100 if photo.thumb_height > photo.thumb_width else (photo.thumb_height * 100 / photo.thumb_width)|int %}
                
                var marker = L.marker([{{ (min_lat + max_lat) / 2 }}, {{ (min_lon + max_lon) / 2 }}], {
                    icon: L.divIcon({
                        html: '<div class="custom-marker"><img src="{{ photo.thumbnail_path }}" style="width: {{ display_width }}px; height: {{ display_height }}px;"></div>',
                        className: '',
                        iconSize: [{{ display_width }}, {{ display_height }}]
                    }),
                    thumbnail: "{{ photo.thumbnail_path }}",
                    photoPath: "{{ photo.photo_path }}",
                    photoDate: "{{ photo.photo_date }}",
                    shootTime: {{ photo.shoot_time.timestamp() if photo.shoot_time else 'Number.MAX_VALUE' }},
                    thumbWidth: {{ photo.thumb_width }},
                    thumbHeight: {{ photo.thumb_height }}
                });
                {% endif %}

                marker.on('click', function(e) {
                    // 获取照片信息
                    var photoPath = e.target.options.photoPath;
                    var photoDate = e.target.options.photoDate;
                    var shootTime = e.target.options.shootTime;
                    var thumbPath = e.target.options.thumbnail;
                    var thumbWidth = e.target.options.thumbWidth;
                    var thumbHeight = e.target.options.thumbHeight;
                    
                    // 直接显示照片，不再判断地图缩放级别
                    showFullImage([{
                        photo_path: photoPath,
                        photo_date: photoDate,
                        shoot_time: shootTime,
                        thumb_path: thumbPath,
                        thumb_width: thumbWidth,
                        thumb_height: thumbHeight
                    }], 0);
                });

                markers.addLayer(marker);
            {% endfor %}

            map.addLayer(markers);

            // 设置地图视图以适应所有标记
            var bounds = [[{{ min_lat }}, {{ min_lon }}], [{{ max_lat }}, {{ max_lon }}]];
            map.fitBounds(bounds);

            function groupByMonth(photos) {
                var grouped = {};
                photos.forEach(photo => {
                    var shootTime = photo.shootTime;
                    if (shootTime != Number.MAX_VALUE) {
                        var date = new Date(shootTime * 1000);
                        var year = date.getUTCFullYear();
                        var month = date.getUTCMonth() + 1;
                        var key = year + '-' + (month < 10 ? '0' + month : month);
                        if (!grouped[key]) {
                            grouped[key] = [];
                        }
                        grouped[key].push(photo);
                    } else {
                        if (!grouped['Unknown']) {
                            grouped['Unknown'] = [];
                        }
                        grouped['Unknown'].push(photo);
                    }
                });
                return grouped;
            }
            
            function showCustomPopUp(markers) {
                // 修改：移除对地图缩放级别的检查，直接显示照片列表
                // if (map.getZoom() !== map.getMaxZoom()) {
                //     map.setZoom(map.getMaxZoom());
                //     return;
                // }

                var photos = Array.isArray(markers) ? markers : markers.map(marker => ({
                    photo_path: marker.options.photoPath,
                    photo_date: marker.options.photoDate,
                    shoot_time: marker.options.shootTime || Number.MAX_VALUE,
                    thumb_path: marker.options.thumbnail,
                    thumb_width: marker.options.thumbWidth,
                    thumb_height: marker.options.thumbHeight
                }));
                
                // Sort photos by shoot time
                photos.sort((a, b) => a.shoot_time - b.shoot_time);
                currentClusterPhotos = photos;
                
                // Create modal container
                var modalContainer = document.createElement('div');
                modalContainer.className = 'custom-cluster-pop-up';
                modalContainer.style.width = '92vw';
                modalContainer.style.height = '88vh';
                modalContainer.style.backgroundColor = 'white';
                modalContainer.style.borderRadius = '20px';
                modalContainer.style.boxShadow = '0 15px 50px rgba(0,0,0,0.25)';
                modalContainer.style.display = 'flex';
                modalContainer.style.flexDirection = 'column';
                modalContainer.style.overflow = 'hidden';
                modalContainer.style.zIndex = '1000';
                modalContainer.style.border = '1px solid rgba(255,255,255,0.2)';
                modalContainer.style.backdropFilter = 'blur(5px)';
                
                // Add header with title and close button
                var headerDiv = document.createElement('div');
                headerDiv.style.padding = '20px 25px';
                headerDiv.style.borderBottom = '1px solid rgba(0,0,0,0.06)';
                headerDiv.style.display = 'flex';
                headerDiv.style.justifyContent = 'space-between';
                headerDiv.style.alignItems = 'center';
                headerDiv.style.background = 'linear-gradient(to right, #f8f9fa, #ffffff)';
                headerDiv.style.boxShadow = '0 2px 10px rgba(0,0,0,0.03)';
                headerDiv.style.position = 'relative';
                headerDiv.style.zIndex = '2';
                
                var titleText = `<h3 style="margin: 0; font-family: '等线', 'Microsoft YaHei', sans-serif; font-weight: bold; font-size: 22px; background: linear-gradient(to right, #ff416c, #ff4b2b); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">照片列表 <span style="background: linear-gradient(to right, #ff416c, #ff4b2b); color: white; padding: 4px 10px; border-radius: 20px; font-size: 18px; margin-left: 10px; -webkit-text-fill-color: white; box-shadow: 0 3px 8px rgba(255, 65, 108, 0.3);">${photos.length}</span></h3>`;
                
                headerDiv.innerHTML = `
                    ${titleText}
                    <span class="closebtn">×</span>
                `;
                modalContainer.appendChild(headerDiv);
                
                // Create content container
                var contentContainer = document.createElement('div');
                contentContainer.style.display = 'flex';
                contentContainer.style.flexDirection = 'column';
                contentContainer.style.flex = '1';
                contentContainer.style.overflow = 'hidden';
                contentContainer.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ed 100%)';
                contentContainer.style.position = 'relative';
                modalContainer.appendChild(contentContainer);
                
                                // Create thumbnails container
                var thumbnailsContainer = document.createElement('div');
                thumbnailsContainer.style.flex = '1';
                thumbnailsContainer.style.position = 'relative';
                thumbnailsContainer.style.overflow = 'hidden';
                thumbnailsContainer.style.marginBottom = '20px'; // 设置为20px
                contentContainer.appendChild(thumbnailsContainer);
                
                // Create pagination container at the bottom
                var paginationContainer = document.createElement('div');
                paginationContainer.className = 'pagination';
                paginationContainer.style.padding = '15px 0';
                paginationContainer.style.display = 'flex';
                paginationContainer.style.justifyContent = 'center';
                paginationContainer.style.gap = '8px';
                paginationContainer.style.borderTop = '1px solid rgba(0,0,0,0.06)';
                paginationContainer.style.background = 'linear-gradient(to right, #f8f9fa, #ffffff)';
                paginationContainer.style.boxShadow = '0 -2px 10px rgba(0,0,0,0.03)';
                contentContainer.appendChild(paginationContainer);
                
                // Pagination variables
                var photosPerPage = 21; // 7 columns × 3 rows (fixed grid size)
                var totalPages = Math.ceil(photos.length / photosPerPage);
                var currentPage = 0;
                
                // 保存当前页面内容用于动画过渡
                var currentPageContent = null;
                
                function displayPage(page, direction = 'none') {
                    // 更新当前页面
                    currentPage = page;
                    
                    // 创建新的内容容器
                    var newThumbnailsGrid = document.createElement('div');
                    newThumbnailsGrid.className = 'thumbnails-grid';
                    newThumbnailsGrid.style.position = 'absolute';
                    newThumbnailsGrid.style.top = '0';
                    newThumbnailsGrid.style.left = '0';
                    newThumbnailsGrid.style.right = '0';
                    newThumbnailsGrid.style.bottom = '0'; // 铺满整个容器
                    newThumbnailsGrid.style.overflow = 'hidden';
                    newThumbnailsGrid.style.padding = '20px'; // 保持内边距
                    newThumbnailsGrid.style.display = 'grid';
                    newThumbnailsGrid.style.gridTemplateColumns = 'repeat(7, 1fr)';
                    newThumbnailsGrid.style.gridTemplateRows = 'repeat(3, 1fr)';
                    newThumbnailsGrid.style.gap = '16px'; // 保持网格间距
                    newThumbnailsGrid.style.alignContent = 'stretch';
                    newThumbnailsGrid.style.justifyContent = 'stretch';
                    newThumbnailsGrid.style.height = 'calc(100% - 15px)'; // 调整高度以减少空白区域
                    
                    // 设置动画初始位置
                    if (direction === 'next') {
                        newThumbnailsGrid.style.transform = 'translateX(100%)'
                    } else if (direction === 'prev') {
                        newThumbnailsGrid.style.transform = 'translateX(-100%)'
                    }
                    
                    // 添加过渡动画
                    newThumbnailsGrid.style.transition = 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
                    
                    var start = page * photosPerPage;
                    var end = Math.min(start + photosPerPage, photos.length);
                    var pagePhotos = photos.slice(start, end);
                    
                    // Create a copy of pagePhotos with original indices before sorting
                    var indexedPhotos = pagePhotos.map((photo, index) => ({
                        photo: photo,
                        originalIndex: start + index
                    }));
                    
                    // Sort photos by aspect ratio for better layout, but keep track of original indices
                    indexedPhotos.sort((a, b) => {
                        var ratioA = a.photo.thumb_width / a.photo.thumb_height;
                        var ratioB = b.photo.thumb_width / b.photo.thumb_height;
                        return ratioA - ratioB;
                    });
                    
                    indexedPhotos.forEach((item, idx) => {
                        var photo = item.photo;
                        var originalIndex = item.originalIndex;
                        
                        // 创建照片容器
                        var thumbContainer = document.createElement('div');
                        thumbContainer.style.position = 'relative';
                        thumbContainer.style.cursor = 'pointer';
                        thumbContainer.style.display = 'flex';
                        thumbContainer.style.alignItems = 'center';
                        thumbContainer.style.justifyContent = 'center';
                        thumbContainer.style.height = '100%'; // 使用容器的完整高度
                        thumbContainer.style.overflow = 'hidden';
                        thumbContainer.style.borderRadius = '12px'; // 稍微减少圆角
                        thumbContainer.style.backgroundColor = 'white';
                        thumbContainer.style.transition = 'all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1)';
                        thumbContainer.style.boxShadow = '0 5px 15px rgba(0,0,0,0.08)';
                        thumbContainer.style.transform = 'translateY(0)';
                        
                        // Add hover effects
                        thumbContainer.onmouseenter = function() {
                            this.style.transform = 'translateY(-8px)';
                            this.style.boxShadow = '0 15px 30px rgba(0,0,0,0.15)';
                        };
                        thumbContainer.onmouseleave = function() {
                            this.style.transform = 'translateY(0)';
                            this.style.boxShadow = '0 5px 15px rgba(0,0,0,0.08)';
                        };
                        
                        var thumbImg = document.createElement('img');
                        thumbImg.src = photo.thumb_path;
                        thumbImg.style.width = '100%';
                        thumbImg.style.height = '100%';
                        thumbImg.style.objectFit = 'cover';
                        thumbImg.style.borderRadius = '12px';
                        thumbImg.style.transition = 'all 0.3s ease';
                        thumbImg.style.padding = '0';
                        
                        var dateLabel = document.createElement('div');
                        dateLabel.textContent = photo.photo_date || '未知日期';
                        dateLabel.style.position = 'absolute';
                        dateLabel.style.bottom = '0';
                        dateLabel.style.left = '0';
                        dateLabel.style.right = '0';
                        dateLabel.style.background = 'linear-gradient(to right, rgba(0,0,0,0.8), rgba(0,0,0,0.6))';
                        dateLabel.style.color = 'white';
                        dateLabel.style.padding = '8px 10px';
                        dateLabel.style.fontSize = '13px';
                        dateLabel.style.textAlign = 'center';
                        dateLabel.style.fontFamily = "'等线', 'Microsoft YaHei', sans-serif";
                        dateLabel.style.fontWeight = 'bold';
                        dateLabel.style.borderBottomLeftRadius = '16px';
                        dateLabel.style.borderBottomRightRadius = '16px';
                        
                        thumbContainer.appendChild(thumbImg);
                        thumbContainer.appendChild(dateLabel);
                        newThumbnailsGrid.appendChild(thumbContainer);
                        
                        thumbContainer.onclick = function() {
                            // 确保LightGallery实例已销毁后再打开新的查看器
                            if (window.lgInstance) {
                                window.lgInstance.destroy();
                                window.lgInstance = null;
                            }
                            // 延迟一下再显示，确保销毁操作完成
                            setTimeout(function() {
                                showFullImage(photos, originalIndex);
                            }, 50);
                        };
                    });
                    
                    // 添加到缩略图容器中
                    thumbnailsContainer.appendChild(newThumbnailsGrid);
                    
                    // 执行动画
                    if (currentPageContent) {
                        // 设置当前内容的初始位置
                        if (direction === 'next') {
                            currentPageContent.style.transform = 'translateX(0)'
                        } else if (direction === 'prev') {
                            currentPageContent.style.transform = 'translateX(0)'
                        }
                        
                        // 强制重绘
                        newThumbnailsGrid.offsetHeight;
                        
                        // 执行动画
                        if (direction === 'next') {
                            currentPageContent.style.transform = 'translateX(-100%)'
                            newThumbnailsGrid.style.transform = 'translateX(0)'
                        } else if (direction === 'prev') {
                            currentPageContent.style.transform = 'translateX(100%)'
                            newThumbnailsGrid.style.transform = 'translateX(0)'
                        }
                        
                        // 动画完成后移除旧内容
                        setTimeout(() => {
                            if (currentPageContent && currentPageContent.parentNode) {
                                currentPageContent.parentNode.removeChild(currentPageContent);
                            }
                            // 确保新内容可见
                            newThumbnailsGrid.style.transform = 'translateX(0)';
                        }, 400);
                    } else {
                        // 第一次显示，直接显示新内容
                        newThumbnailsGrid.style.transform = 'translateX(0)';
                        // 确保内容可见
                        setTimeout(() => {
                            newThumbnailsGrid.style.transform = 'translateX(0)';
                        }, 50);
                    }
                    
                    // 更新当前页面内容引用
                    // 延迟更新引用，确保动画完成
                    setTimeout(() => {
                        currentPageContent = newThumbnailsGrid;
                    }, 400);
                    
                    // Update pagination buttons
                    paginationContainer.innerHTML = '';
                    if (totalPages > 1) {
                        // Previous button
                        var prevButton = document.createElement('button');
                        prevButton.textContent = '上一页';
                        prevButton.disabled = page === 0;
                        prevButton.onclick = () => {
                            if (page > 0) displayPage(page - 1, 'prev');
                        };
                        paginationContainer.appendChild(prevButton);
                        
                        // Page buttons 
                        // Show at most 7 page buttons, with ellipsis if needed
                        var maxButtons = 7;
                        var startPage = Math.max(0, Math.min(page - Math.floor(maxButtons / 2), totalPages - maxButtons));
                        var endPage = Math.min(startPage + maxButtons, totalPages);
                        
                        if (startPage > 0) {
                            var firstPageButton = document.createElement('button');
                            firstPageButton.textContent = '1';
                            firstPageButton.onclick = () => displayPage(0, page > 0 ? 'prev' : 'next');
                            paginationContainer.appendChild(firstPageButton);
                            
                            if (startPage > 1) {
                                var ellipsisButton = document.createElement('span');
                                ellipsisButton.textContent = '...';
                                ellipsisButton.style.margin = '0 5px';
                                ellipsisButton.style.alignSelf = 'center';
                                ellipsisButton.style.color = '#666';
                                paginationContainer.appendChild(ellipsisButton);
                            }
                        }
                        
                        for (var i = startPage; i < endPage; i++) {
                            var pageButton = document.createElement('button');
                            pageButton.textContent = i + 1;
                            pageButton.className = i === page ? 'active' : '';
                            pageButton.onclick = (function(pageNum) {
                                return function() {
                                    var dir = pageNum > page ? 'next' : 'prev';
                                    displayPage(pageNum, dir);
                                };
                            })(i);
                            paginationContainer.appendChild(pageButton);
                        }
                        
                        if (endPage < totalPages) {
                            if (endPage < totalPages - 1) {
                                var ellipsisButton = document.createElement('span');
                                ellipsisButton.textContent = '...';
                                ellipsisButton.style.margin = '0 5px';
                                ellipsisButton.style.alignSelf = 'center';
                                ellipsisButton.style.color = '#666';
                                paginationContainer.appendChild(ellipsisButton);
                            }
                            
                            var lastPageButton = document.createElement('button');
                            lastPageButton.textContent = totalPages;
                            lastPageButton.onclick = () => {
                                var dir = totalPages - 1 > page ? 'next' : 'prev';
                                displayPage(totalPages - 1, dir);
                            };
                            paginationContainer.appendChild(lastPageButton);
                        }
                        
                        // Next button
                        var nextButton = document.createElement('button');
                        nextButton.textContent = '下一页';
                        nextButton.disabled = page === totalPages - 1;
                        nextButton.onclick = () => {
                            if (page < totalPages - 1) displayPage(page + 1, 'next');
                        };
                        paginationContainer.appendChild(nextButton);
                    }
                    
                    // Add jump info text
                    if (totalPages > 1) {
                        var pageInfoText = document.createElement('div');
                        pageInfoText.style.marginLeft = '15px';
                        pageInfoText.style.color = '#666';
                        pageInfoText.style.fontSize = '14px';
                        pageInfoText.style.display = 'flex';
                        pageInfoText.style.alignItems = 'center';
                        pageInfoText.innerHTML = `第 <strong style="color:#ff416c;margin:0 5px;">${page + 1}</strong> 页，共 <strong style="color:#ff416c;margin:0 5px;">${totalPages}</strong> 页`;
                        paginationContainer.appendChild(pageInfoText);
                    }
                }
                
                displayPage(0);
                
                // 添加鼠标滚轮事件监听器
                modalContainer.addEventListener('wheel', function(event) {
                    // 阻止默认的滚动行为
                    event.preventDefault();
                    
                    // 阻止事件冒泡
                    event.stopPropagation();
                    
                    // 判断滚轮方向
                    if (event.deltaY > 0) {
                        // 向下滚动，切换到下一页
                        if (currentPage < totalPages - 1) {
                            displayPage(currentPage + 1, 'next');
                        }
                    } else {
                        // 向上滚动，切换到上一页
                        if (currentPage > 0) {
                            displayPage(currentPage - 1, 'prev');
                        }
                    }
                });
                
                document.body.appendChild(modalContainer);
                var closeBtn = modalContainer.querySelector('.closebtn');
                closeBtn.addEventListener('click', function() {
                    modalContainer.style.opacity = '0';
                    modalContainer.style.transform = 'translate(-50%, -50%) scale(0.9)';
                    setTimeout(() => {
                        document.body.removeChild(modalContainer);
                        currentCustomPopUp = null;
                    }, 300);
                });
                
                currentCustomPopUp = modalContainer;
                modalContainer.style.opacity = '0';
                modalContainer.style.transform = 'translate(-50%, -50%) scale(0.9)';
                setTimeout(() => {
                    modalContainer.style.opacity = '1';
                    modalContainer.style.transform = 'translate(-50%, -50%) scale(1)';
                }, 10);
            }

            function displayPage(page, photos, photosPerPage, popUp, lg) {
                var start = page * photosPerPage;
                var end = Math.min(start + photosPerPage, photos.length);
                var pagePhotos = photos.slice(start, end);
                var thumbnailsDiv = document.createElement('div');
                thumbnailsDiv.className = 'thumbnails';
                pagePhotos.forEach((photo, index) => {
                    var thumbImg = document.createElement('a');
                    thumbImg.href = photo.photo_path;
                    thumbImg.setAttribute('data-lg-size', `${photo.thumb_width}-${photo.thumb_height}`);
                    thumbImg.setAttribute('data-index', start + index);
                    thumbImg.innerHTML = `<img src="${photo.thumb_path}" width="${photo.thumb_width / 2}" height="${photo.thumb_height / 2}">`;
                    thumbImg.onclick = function(e) {
                        e.preventDefault();
                        lg.open(start + index);
                    };
                    thumbnailsDiv.appendChild(thumbImg);
                });
                var oldThumbnailsDiv = popUp.querySelector('.thumbnails');
                if (oldThumbnailsDiv) {
                    popUp.replaceChild(thumbnailsDiv, oldThumbnailsDiv);
                } else {
                    popUp.appendChild(thumbnailsDiv);
                }
            }
            function showFullImage(photos, currentIndex) {
                var lgContainer = document.getElementById('lightgallery');
                if (!lgContainer) {
                    lgContainer = document.createElement('div');
                    lgContainer.id = 'lightgallery';
                    lgContainer.style.display = 'none';
                    document.body.appendChild(lgContainer);
                } else {
                    // 清空现有内容，但确保不会影响到正在显示的实例
                    if (!window.lgInstance) {
                        lgContainer.innerHTML = '';
                    }
                }

                // 如果lightgallery实例已经存在，先销毁它
                if (window.lgInstance) {
                    window.lgInstance.destroy();
                    window.lgInstance = null;
                }

                // 只有在容器为空或需要重新创建时才添加内容
                if (lgContainer.innerHTML.trim() === '') {
                    photos.forEach((photo, index) => {
                        var a = document.createElement('a');
                        a.href = photo.photo_path;
                        
                        // 确保图片路径正确加载
                        a.setAttribute('data-src', photo.photo_path);
                        
                        // 添加缩略图路径，提高加载效率
                        if (photo.thumb_path) {
                            a.setAttribute('data-thumb', photo.thumb_path);
                        }
                        
                        // 提取文件名和扩展名
                        var fileName = photo.photo_path.split('/').pop();
                        
                        // 存储照片详细信息供信息面板使用
                        var photoInfoHtml = `
                            <div class="lg-photo-info">
                                <h3>照片信息</h3>
                                <table>
                                    <tr>
                                        <td><strong>文件名：</strong></td>
                                        <td>${fileName}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>拍摄时间：</strong></td>
                                        <td>${photo.photo_date || '未知'}</td>
                                    </tr>
                                </table>
                            </div>
                        `;
                        a.setAttribute('data-photo-info', photoInfoHtml);
                        
                        // 添加日期标签到顶部和底部
                        a.setAttribute('data-sub-html', `
                            <div style="position:fixed;top:10px;left:0;right:0;text-align:center;z-index:9999;">
                                <p class="photo-date" style="display:inline-block;background:linear-gradient(to right, #ff416c, #ff4b2b);color:white;padding:8px 16px;border-radius:30px;font-family:'等线','Microsoft YaHei',sans-serif;font-weight:bold;font-size:18px;box-shadow:0 4px 12px rgba(255,65,108,0.4);">${photo.photo_date || '未知日期'}</p>
                            </div>
                            <div style="text-align:center;margin-top:15px;">
                                <p class="photo-date-bottom">${photo.photo_date || '未知日期'}</p>
                            </div>
                        `);
                        
                        // 改进图片加载方式，使用完整的img标签
                        a.innerHTML = `<img src="${photo.thumb_path || photo.photo_path}" alt="${photo.photo_date || '未知日期'}" loading="lazy">`;
                        lgContainer.appendChild(a);
                    });
                }

                if (window.lgInstance) {
                    window.lgInstance.destroy();
                    window.lgInstance = null;
                }
                
                // 动态创建旋转和信息按钮
                var rotateLeftBtn = '<button type="button" aria-label="向左旋转90度" class="lg-rotate-left lg-icon"><i class="fa-solid fa-rotate-left"></i></button>';
                var rotateRightBtn = '<button type="button" aria-label="向右旋转90度" class="lg-rotate-right lg-icon"><i class="fa-solid fa-rotate-right"></i></button>';
                var infoBtn = '<button type="button" aria-label="查看详细信息" class="lg-info-btn lg-icon"><i class="fa-solid fa-circle-info"></i></button>';
                
                // 配置LightGallery，添加所有增强功能
                window.lgInstance = lightGallery(lgContainer, {
                    plugins: [lgZoom, lgFullscreen, lgRotate, lgHash, lgThumbnail],
                    speed: 300,
                    download: false,
                    counter: true,
                    dynamic: false,
                    index: currentIndex,
                    mode: 'lg-slide', // 改为slide模式以支持切换动画
                    enableDrag: true,
                    enableSwipe: true,
                    preload: 2,
                    closable: true,
                    showAfterLoad: true,
                    selector: 'a',
                    closeOnTap: false, // 防止误触关闭
                    hideBarsDelay: 5000,
                    loop: true,
                    thumbnail: true,
                    pager: false,
                    appendSubHtmlTo: '.lg-content',
                    addClass: 'lg-photo-view',
                    
                    // 缩放配置，启用鼠标滚轮和拖动
                    zoom: {
                        scroll: true,
                        actualSize: true,
                        mousewheel: true,
                        toggleZoomWheel: false, // 始终启用滚轮缩放，不需要按键切换
                        enableZoomAfter: 0, // 立即允许缩放
                        scale: 3, // 提高最大缩放倍数
                        zoomBy: 0.5, // 每次滚轮缩放的步长
                        maxZoom: 3, // 最大缩放倍数
                        minZoom: 1, // 最小缩放倍数
                        pinchToZoom: true, // 启用触摸屏缩放
                        mouseMovePan: true, // 启用鼠标移动平移
                        mouseMovePanSpeed: 0.5 // 平移速度
                    },
                    
                    // 旋转配置
                    rotate: {
                        rotateLeft: true,
                        rotateRight: true,
                        flipHorizontal: false,
                        flipVertical: false,
                    },
                    
                    hash: false,
                    
                    // 自定义模板，添加详细信息面板
                    template: `
                        <div class="lg-container lg-backdrop">
                            <div class="lg-inner">
                                <div class="lg-toolbar lg-group">
                                </div>
                                <div class="lg-content"></div>
                                <div class="lg-info-panel" style="display: none;">
                                    <div class="lg-info-panel-inner"></div>
                                </div>
                                <div class="lg-prev lg-icon">‹</div>
                                <div class="lg-next lg-icon">›</div>
                                <div class="lg-thumb-outer">
                                    <div class="lg-thumb lg-group"></div>
                                </div>
                                <div class="lg-pager-outer"></div>
                                <div class="lg-vertical-buttons">
                                </div>
                            </div>
                        </div>
                    `
                });
                
                // 添加事件监听器，在关闭时清理实例
                document.addEventListener('lgClose', function(event) {
                    console.log('LightGallery已关闭');
                    // 延迟清理window.lgInstance，避免其他代码尝试访问
                    setTimeout(function() {
                        window.lgInstance = null;
                    }, 100);
                }, { once: false });

                // 打开图库
                window.lgInstance.openGallery(currentIndex);
                
                // 添加鼠标滚轮事件监听器，实现上一张/下一张切换
                var lgContainerElement = document.querySelector('.lg-container');
                if (lgContainerElement) {
                    lgContainerElement.addEventListener('wheel', function(event) {
                        // 阻止默认的滚动行为
                        event.preventDefault();
                        
                        // 阻止事件冒泡
                        event.stopPropagation();
                        
                        // 检查是否正在切换动画中
                        if (lgContainerElement.classList.contains('lg-animating')) {
                            return;
                        }
                        
                        // 添加动画中类以防止连续滚动
                        lgContainerElement.classList.add('lg-animating');
                        
                        // 判断滚轮方向
                        if (event.deltaY > 0) {
                            // 向下滚动，切换到下一张
                            if (window.lgInstance && typeof window.lgInstance.goToNextSlide === 'function') {
                                window.lgInstance.goToNextSlide();
                            }
                        } else {
                            // 向上滚动，切换到上一张
                            if (window.lgInstance && typeof window.lgInstance.goToPrevSlide === 'function') {
                                window.lgInstance.goToPrevSlide();
                            }
                        }
                        
                        // 动画完成后移除动画中类
                        setTimeout(function() {
                            lgContainerElement.classList.remove('lg-animating');
                        }, 300);
                    });
                }
                
                // 添加事件处理，自定义功能实现
                setTimeout(function() {
                    // 确保LightGallery完全加载
                    var initVerticalButtons = function() {
                        // 移除之前可能存在的垂直按钮容器
                        var oldVerticalButtons = document.querySelector('.lg-vertical-buttons');
                        if (oldVerticalButtons) {
                            oldVerticalButtons.remove();
                        }
                        
                        // 创建新的垂直按钮容器
                        var verticalButtons = document.createElement('div');
                        verticalButtons.className = 'lg-vertical-buttons';
                        
                        // 获取LightGallery容器，确保添加到正确的容器中
                        var lgContainer = document.querySelector('.lg-container');
                        if (lgContainer) {
                            lgContainer.appendChild(verticalButtons);
                            
                            // 清空容器并创建所有按钮
                            verticalButtons.innerHTML = '';
                            
                            // 创建关闭按钮
                            var closeBtn = document.createElement('button');
                            closeBtn.className = 'lg-btn lg-close-btn';
                            closeBtn.innerHTML = '<i class="fa-solid fa-times"></i>';
                            closeBtn.setAttribute('aria-label', '关闭');
                            closeBtn.addEventListener('click', function() {
                                if (window.lgInstance) {
                                    window.lgInstance.destroy();
                                    window.lgInstance = null;
                                }
                            });
                            verticalButtons.appendChild(closeBtn);
                            
                            // 添加点击背景关闭功能
                            lgContainer.addEventListener('click', function(e) {
                                // 检查是否点击在背景上（而不是图片内容上）
                                if (e.target.classList.contains('lg-container') || e.target.classList.contains('lg-backdrop')) {
                                    if (window.lgInstance) {
                                        window.lgInstance.destroy();
                                        window.lgInstance = null;
                                    }
                                }
                            });
                            
                            // 创建并添加旋转左按钮
                            var rotateLeftBtn = document.createElement('button');
                            rotateLeftBtn.className = 'lg-btn lg-rotate-left-btn';
                            rotateLeftBtn.innerHTML = '<i class="fa-solid fa-rotate-left"></i>';
                            rotateLeftBtn.setAttribute('aria-label', '向左旋转90度');
                            rotateLeftBtn.addEventListener('click', function() {
                                if (window.lgInstance) {
                                    try {
                                        // 直接调用rotate方法，不依赖插件对象
                                        var degrees = -90;
                                        var currentImage = document.querySelector('.lg-current .lg-image');
                                        if (currentImage) {
                                            // 获取当前旋转角度
                                            var currentTransform = currentImage.style.transform || '';
                                            var currentRotation = 0;
                                            var rotateMatch = currentTransform.match(/rotate\((-?\d+)deg\)/);
                                            if (rotateMatch) {
                                                currentRotation = parseInt(rotateMatch[1]);
                                            }
                                            
                                            // 计算新的旋转角度
                                            var newRotation = currentRotation + degrees;
                                            
                                            // 应用新的旋转
                                            var newTransform = currentTransform.replace(/rotate\(-?\d+deg\)/, '');
                                            newTransform += ' rotate(' + newRotation + 'deg)';
                                            currentImage.style.transform = newTransform.trim();
                                            
                                            console.log('向左旋转成功，当前角度：' + newRotation);
                                        } else {
                                            console.error('找不到当前图片元素');
                                        }
                                    } catch (e) {
                                        console.error('旋转失败：', e);
                                    }
                                }
                            });
                            verticalButtons.appendChild(rotateLeftBtn);
                            
                            // 创建并添加旋转右按钮
                            var rotateRightBtn = document.createElement('button');
                            rotateRightBtn.className = 'lg-btn lg-rotate-right-btn';
                            rotateRightBtn.innerHTML = '<i class="fa-solid fa-rotate-right"></i>';
                            rotateRightBtn.setAttribute('aria-label', '向右旋转90度');
                            rotateRightBtn.addEventListener('click', function() {
                                if (window.lgInstance) {
                                    try {
                                        // 直接调用rotate方法，不依赖插件对象
                                        var degrees = 90;
                                        var currentImage = document.querySelector('.lg-current .lg-image');
                                        if (currentImage) {
                                            // 获取当前旋转角度
                                            var currentTransform = currentImage.style.transform || '';
                                            var currentRotation = 0;
                                            var rotateMatch = currentTransform.match(/rotate\((-?\d+)deg\)/);
                                            if (rotateMatch) {
                                                currentRotation = parseInt(rotateMatch[1]);
                                            }
                                            
                                            // 计算新的旋转角度
                                            var newRotation = currentRotation + degrees;
                                            
                                            // 应用新的旋转
                                            var newTransform = currentTransform.replace(/rotate\(-?\d+deg\)/, '');
                                            newTransform += ' rotate(' + newRotation + 'deg)';
                                            currentImage.style.transform = newTransform.trim();
                                            
                                            console.log('向右旋转成功，当前角度：' + newRotation);
                                        } else {
                                            console.error('找不到当前图片元素');
                                        }
                                    } catch (e) {
                                        console.error('旋转失败：', e);
                                    }
                                }
                            });
                            verticalButtons.appendChild(rotateRightBtn);
                            
                            // 创建并添加信息按钮
                            var infoBtn = document.createElement('button');
                            infoBtn.className = 'lg-btn lg-info-btn';
                            infoBtn.innerHTML = '<i class="fa-solid fa-circle-info"></i>';
                            infoBtn.setAttribute('aria-label', '查看详细信息');
                            
                            // 确保信息按钮点击事件
                            infoBtn.addEventListener('click', function() {
                                try {
                                    console.log('信息按钮被点击');
                                    
                                    // 直接查找和创建信息面板
                                    var infoPanel = document.querySelector('.lg-info-panel');
                                    if (!infoPanel) {
                                        console.log('信息面板不存在，创建新面板');
                                        infoPanel = document.createElement('div');
                                        infoPanel.className = 'lg-info-panel';
                                        infoPanel.style.display = 'none';
                                        infoPanel.innerHTML = '<div class="lg-info-panel-inner"></div>';
                                        var lgContainer = document.querySelector('.lg-container');
                                        if (lgContainer) {
                                            lgContainer.appendChild(infoPanel);
                                        }
                                    }
                                    
                                    if (window.lgInstance) {
                                        var currentIndex = window.lgInstance.index;
                                        var links = document.querySelectorAll('#lightgallery a');
                                        
                                        console.log('当前索引:', currentIndex, '链接数量:', links.length);
                                        
                                        if (links && links.length > currentIndex) {
                                            var photoInfo = links[currentIndex].getAttribute('data-photo-info');
                                            console.log('获取到照片信息:', photoInfo ? '成功' : '失败');
                                            
                                            // 更新信息面板内容
                                            var infoPanelInner = infoPanel.querySelector('.lg-info-panel-inner');
                                            if (infoPanelInner) {
                                                infoPanelInner.innerHTML = photoInfo || '没有可用的照片信息';
                                            }
                                            
                                            // 切换显示状态
                                            var isShowing = (infoPanel.style.display !== 'none' && infoPanel.classList.contains('show'));
                                            
                                            if (!isShowing) {
                                                // 显示面板
                                                console.log('显示信息面板');
                                                infoPanel.style.display = 'block';
                                                
                                                // 使用requestAnimationFrame确保DOM更新后再添加显示类
                                                requestAnimationFrame(function() {
                                                    requestAnimationFrame(function() {
                                                        infoPanel.classList.add('show');
                                                    });
                                                });
                                            } else {
                                                // 隐藏面板
                                                console.log('隐藏信息面板');
                                                infoPanel.classList.remove('show');
                                                
                                                // 延迟隐藏元素，等待过渡效果完成
                                                setTimeout(function() {
                                                    infoPanel.style.display = 'none';
                                                }, 400); // 确保这个时间不小于CSS过渡时间
                                            }
                                        } else {
                                            console.error('找不到当前照片数据，links:', links ? links.length : 0, 'currentIndex:', currentIndex);
                                        }
                                    } else {
                                        console.error('LightGallery实例不存在');
                                    }
                                } catch (e) {
                                    console.error('显示信息面板失败：', e);
                                }
                            });
                            verticalButtons.appendChild(infoBtn);
                            
                            // 设置按钮容器的样式，确保在正确位置
                            verticalButtons.style.position = 'fixed';
                            verticalButtons.style.top = '15px';
                            verticalButtons.style.right = '15px';
                            verticalButtons.style.display = 'flex';
                            verticalButtons.style.flexDirection = 'column';
                            verticalButtons.style.gap = '20px';
                            verticalButtons.style.zIndex = '9999';
                            
                            console.log('垂直按钮栏设置完成');
                        } else {
                            console.error('未找到LightGallery容器');
                        }
                    };
                    
                    // 立即执行一次
                    initVerticalButtons();
                    
                    // 100ms后再执行一次以确保DOM完全载入
                    setTimeout(initVerticalButtons, 100);
                    
                    // 300ms后再执行一次以确保所有资源加载完成
                    setTimeout(initVerticalButtons, 300);
                    
                    // 监听LightGallery事件
                    if (typeof window.lgAfterSlideListener === 'undefined') {
                        window.lgAfterSlideListener = true;
                        document.addEventListener('lgAfterSlide', function() {
                            setTimeout(initVerticalButtons, 100);
                            
                            // 重置当前图片的旋转角度
                            setTimeout(function() {
                                var currentImage = document.querySelector('.lg-current .lg-image');
                                if (currentImage) {
                                    // 移除旋转样式，回到原始状态
                                    var currentTransform = currentImage.style.transform || '';
                                    currentImage.style.transform = currentTransform.replace(/rotate\(-?\d+deg\)/, '').trim();
                                    console.log('重置图片旋转状态');
                                }
                            }, 50);
                        });
                        
                        // 监听窗口大小变化事件
                        window.addEventListener('resize', function() {
                            setTimeout(initVerticalButtons, 100);
                        });
                        
                        // 监听键盘事件，支持使用键盘旋转图片
                        document.addEventListener('keydown', function(e) {
                            if (window.lgInstance) {
                                // 左括号键 [ : 向左旋转
                                if (e.key === '[') {
                                    e.preventDefault();
                                    var rotateLeftBtn = document.querySelector('.lg-rotate-left-btn');
                                    if (rotateLeftBtn) {
                                        rotateLeftBtn.click();
                                    }
                                }
                                // 右括号键 ] : 向右旋转
                                else if (e.key === ']') {
                                    e.preventDefault();
                                    var rotateRightBtn = document.querySelector('.lg-rotate-right-btn');
                                    if (rotateRightBtn) {
                                        rotateRightBtn.click();
                                    }
                                }
                                // i 键：显示/隐藏信息面板
                                else if (e.key === 'i') {
                                    e.preventDefault();
                                    var infoBtn = document.querySelector('.lg-info-btn');
                                    if (infoBtn) {
                                        infoBtn.click();
                                    }
                                }
                            }
                        });
                    }
                    
                    // 初始化鹰眼导航
                    setupEagleEye();
                }, 300);
                
                // 实现鹰眼导航功能
                function setupEagleEye() {
                    // 获取鹰眼导航容器
                    var eagleEye = document.querySelector('.lg-eagle-eye');
                    if (!eagleEye) {
                        console.error('未找到鹰眼导航容器');
                        return;
                    }
                    
                    // 确保鹰眼导航容器可见
                    eagleEye.style.display = 'block';
                    
                    // 延迟处理，等待图片加载
                    setTimeout(function() {
                        var image = document.querySelector('.lg-current .lg-image');
                        if (!image) {
                            console.error('未找到当前图片');
                            return;
                        }
                        
                        // 清空鹰眼导航容器
                        eagleEye.innerHTML = '';
                        
                        // 创建鹰眼导航图片
                        var eagleEyeImg = document.createElement('img');
                        eagleEyeImg.className = 'lg-eagle-eye-img';
                        eagleEyeImg.src = image.src;
                        eagleEye.appendChild(eagleEyeImg);
                        
                        // 创建视口指示器
                        var viewport = document.createElement('div');
                        viewport.className = 'lg-eagle-eye-viewport';
                        eagleEye.appendChild(viewport);
                        
                        // 更新鹰眼导航视口
                        updateEagleEyeViewport();
                        
                        // 监听图片移动和缩放事件
                        document.addEventListener('lgAfterSlide', function() {
                            setupEagleEye(); // 切换照片时重新设置鹰眼导航
                        });
                        
                        document.addEventListener('mousemove', function(e) {
                            if (e.target.classList.contains('lg-image')) {
                                updateEagleEyeViewport();
                            }
                        });
                        
                        document.addEventListener('wheel', function(e) {
                            if (e.target.classList.contains('lg-image') || 
                                e.target.closest('.lg-img-wrap')) {
                                setTimeout(updateEagleEyeViewport, 100);
                            }
                        });
                    }, 300);
                }
                
                function updateEagleEyeViewport() {
                    var eagleEye = document.querySelector('.lg-eagle-eye');
                    var viewport = document.querySelector('.lg-eagle-eye-viewport');
                    var image = document.querySelector('.lg-current .lg-image');
                    var imgWrap = document.querySelector('.lg-current .lg-img-wrap');
                    
                    if (!eagleEye || !viewport || !image || !imgWrap) {
                        return;
                    }
                    
                    // 获取图片的变换属性
                    var imgTransform = window.getComputedStyle(image).transform;
                    var imgWrapTransform = window.getComputedStyle(imgWrap).transform;
                    
                    // 计算缩放比例和平移
                    var scale = 1;
                    var translateX = 0;
                    var translateY = 0;
                    
                    if (imgTransform && imgTransform !== 'none') {
                        var matrix = imgTransform.match(/^matrix\((.+)\)$/);
                        if (matrix) {
                            var values = matrix[1].split(', ');
                            scale = parseFloat(values[0]);
                            translateX = parseFloat(values[4]);
                            translateY = parseFloat(values[5]);
                        }
                    }
                    
                    if (imgWrapTransform && imgWrapTransform !== 'none') {
                        var wrapMatrix = imgWrapTransform.match(/^matrix\((.+)\)$/);
                        if (wrapMatrix) {
                            var wrapValues = wrapMatrix[1].split(', ');
                            translateX += parseFloat(wrapValues[4]);
                            translateY += parseFloat(wrapValues[5]);
                        }
                    }
                    
                    // 计算鹰眼视口尺寸和位置
                    var eagleEyeWidth = eagleEye.offsetWidth;
                    var eagleEyeHeight = eagleEye.offsetHeight;
                    var imgDisplayWidth = image.width;
                    var imgDisplayHeight = image.height;
                    var lgContainer = document.querySelector('.lg-container');
                    var containerWidth = lgContainer.offsetWidth;
                    var containerHeight = lgContainer.offsetHeight;
                    
                    // 计算可见区域占图片的比例
                    var visibleWidthRatio = containerWidth / (imgDisplayWidth * scale);
                    var visibleHeightRatio = containerHeight / (imgDisplayHeight * scale);
                    
                    // 确保比例不超过1
                    visibleWidthRatio = Math.min(visibleWidthRatio, 1);
                    visibleHeightRatio = Math.min(visibleHeightRatio, 1);
                    
                    // 计算鹰眼视口的宽高
                    var viewportWidth = eagleEyeWidth * visibleWidthRatio;
                    var viewportHeight = eagleEyeHeight * visibleHeightRatio;
                    
                    // 计算平移比例
                    var translateXRatio = -translateX / (imgDisplayWidth * scale - containerWidth);
                    var translateYRatio = -translateY / (imgDisplayHeight * scale - containerHeight);
                    
                    // 确保比例在0-1之间
                    translateXRatio = Math.max(0, Math.min(translateXRatio, 1));
                    translateYRatio = Math.max(0, Math.min(translateYRatio, 1));
                    
                    // 计算视口位置
                    var viewportLeft = (eagleEyeWidth - viewportWidth) * translateXRatio;
                    var viewportTop = (eagleEyeHeight - viewportHeight) * translateYRatio;
                    
                    // 应用样式
                    viewport.style.width = viewportWidth + 'px';
                    viewport.style.height = viewportHeight + 'px';
                    viewport.style.left = viewportLeft + 'px';
                    viewport.style.top = viewportTop + 'px';
                }
            }

            map.on('click', function() {
                if (currentPopUp) {
                    document.body.removeChild(currentPopUp);
                    currentPopUp = null;
                }
                if (currentCustomPopUp) {
                    document.body.removeChild(currentCustomPopUp);
                    currentCustomPopUp = null;
                }
                
                // 关闭关于窗口
                var aboutDialog = document.querySelector('.about-dialog');
                if (aboutDialog) {
                    document.body.removeChild(aboutDialog);
                }
            });
            
            // 初始化广告区域
            setTimeout(function() {
                // 创建广告容器
                var adContainer = document.createElement('div');
                adContainer.className = 'ad-container';
                document.body.appendChild(adContainer);
                
                // 如果使用的是Google AdSense，可以启用下面的代码
                // var adScript = document.createElement('script');
                // adScript.async = true;
                // adScript.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-YOURPUBLISHERID";
                // adScript.crossOrigin = "anonymous";
                // document.head.appendChild(adScript);
                
                // 设置广告内容
                adContainer.innerHTML = `
                    <div class="ad-wrapper">
                        <div class="ad-header">
                            <span>赞助内容</span>
                            <button class="ad-close-btn">×</button>
                        </div>
                        <div class="ad-content">
                            <!-- 这里可以替换为实际的广告代码 -->
                            <div class="ad-placeholder">
                                <div class="ad-placeholder-text">
                                    <h3>照片地图 Pro 版即将推出</h3>
                                    <p>支持更多高级功能：</p>
                                    <ul>
                                        <li>导出路线轨迹</li>
                                        <li>自定义地图样式</li>
                                        <li>照片编辑功能</li>
                                        <li>多设备同步</li>
                                    </ul>
                                    <button class="ad-cta-button">了解更多</button>
                                </div>
                                <div class="ad-image">
                                    <img src="https://via.placeholder.com/200x150?text=Photo+Map+Pro" alt="照片地图Pro版" onerror="this.src='data:image/svg+xml;charset=utf-8,%3Csvg xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22 width%3D%22200%22 height%3D%22150%22%3E%3Crect width%3D%22200%22 height%3D%22150%22 fill%3D%22%234facfe%22%2F%3E%3Ctext x%3D%22100%22 y%3D%2275%22 text-anchor%3D%22middle%22 alignment-baseline%3D%22middle%22 font-family%3D%22Arial%2C sans-serif%22 font-size%3D%2220%22 fill%3D%22%23fff%22%3E照片地图 Pro%3C%2Ftext%3E%3C%2Fsvg%3E';">
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                // 添加关闭按钮事件
                var closeBtn = adContainer.querySelector('.ad-close-btn');
                if (closeBtn) {
                    closeBtn.addEventListener('click', function() {
                        adContainer.style.transform = 'translateY(100%)';
                        setTimeout(function() {
                            adContainer.style.display = 'none';
                        }, 300);
                    });
                }
                
                // 添加CTA按钮事件
                var ctaButton = adContainer.querySelector('.ad-cta-button');
                if (ctaButton) {
                    ctaButton.addEventListener('click', function() {
                        alert('感谢您的兴趣！Pro版正在开发中，敬请期待。');
                    });
                }
            }, 3000*20*60*2); // 延迟3秒显示广告
        </script>
    </body>
    </html>
    """

    # 使用 Jinja2 模板渲染 HTML
    template = Template(template_str)
    try:
        html_content = template.render(
            min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon,
            photos=all_photos_for_rendering,  # 使用所有照片数据（包括没有GPS信息的照片）
            wechat_qrcode_base64=wechat_qrcode_base64,
            alipay_qrcode_base64=alipay_qrcode_base64
        )
    except Exception as e:
        logging.error(f"模板渲染失败: {str(e)}")
        return None

    # 保存 HTML 文件
    html_path = os.path.join(base_dir, html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # 不再需要复制二维码图片到输出目录，因为已经使用内嵌Base64格式
    # 记录成功信息
    logging.info(f"HTML地图生成成功: {html_path}")
    
    return html_path