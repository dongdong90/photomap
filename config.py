import os

# 高德地图API密钥（请替换为实际密钥，或通过环境变量加载）
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "Your_API_Key_Here")

# 缩略图最大尺寸
THUMBNAIL_SIZE = (500, 500)  # 生成时尺寸，显示时保持原比例

# 照片支持的格式
SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".heic")

# 路径配置
TEMP_DIR_NAME = "photo_temp"
MAP_HTML_NAME = "photo_map.html"