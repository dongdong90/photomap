"""
照片地图工具包 (Photo Map Utilities)
版本: v0.9.1
开发日期: 2024-03
开发者: huanghuadong
版权所有 © 2024 照片地图项目组。保留所有权利。

本模块提供照片地图应用的核心功能，包括：
- GPS信息提取和坐标转换
- 照片EXIF数据处理
- 缩略图生成
- 照片元数据处理
- 智能过滤：自动跳过没有GPS坐标的照片

开源引用说明：
- ExifRead (https://github.com/ianare/exif-py) - 用于读取照片EXIF数据，遵循 BSD License
- Pillow (https://python-pillow.org) - 用于图像处理，遵循 HPND License
"""

import os
import exifread
from PIL import Image, ExifTags
import logging
from datetime import datetime
import math
import piexif
from pillow_heif import register_heif_opener

# 注册HEIF/HEIC格式支持
register_heif_opener()

def wgs84_to_gcj02(lng, lat):
    """WGS84坐标转换为高德地图GCJ-02坐标"""
    def out_of_china(lng, lat):
        return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)

    if out_of_china(lng, lat):
        return lng, lat

    d_lat = transform_lat(lng - 105.0, lat - 35.0)
    d_lng = transform_lng(lng - 105.0, lat - 35.0)
    rad_lat = lat / 180.0 * math.pi
    magic = math.sin(rad_lat)
    magic = 1 - 0.00669342162296594323 * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (6378245.0 / sqrt_magic * math.cos(rad_lat) * math.pi)
    gcj_lng, gcj_lat = lng + d_lng, lat + d_lat
    logging.info(f"坐标转换: WGS84 ({lng}, {lat}) -> GCJ-02 ({gcj_lng}, {gcj_lat})")
    return gcj_lng, gcj_lat

def transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(y / 12.0 * math.pi) + 300.0 * math.sin(y / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def transform_lng(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret

def scan_photos(directory, supported_formats, temp_dir_name):
    """扫描指定目录下支持的图片文件，跳过temp文件夹和thumb文件"""
    photo_list = []
    for root, dirs, files in os.walk(directory):
        if temp_dir_name in dirs:
            dirs.remove(temp_dir_name)
        for file in files:
            if file.lower().endswith(supported_formats) and "thumb" not in file.lower():
                photo_list.append(os.path.join(root, file))
            else:
                logging.warning(f"跳过文件: {file}")
    return photo_list

def get_gps_info(photo_path):
    """
    从照片中提取GPS信息
    
    参考：ExifRead项目的示例代码
    来源：https://github.com/ianare/exif-py/blob/master/examples/
    """
    # 检查是否为HEIC文件
    is_heic = photo_path.lower().endswith('.heic')
    
    # 首先尝试使用exifread处理
    if not is_heic:
        try:
            with open(photo_path, "rb") as f:
                tags = exifread.process_file(f)
                if "GPS GPSLatitude" not in tags or "GPS GPSLongitude" not in tags:
                    logging.warning(f"照片 {photo_path} 没有GPS信息")
                    return None

                lat = tags["GPS GPSLatitude"].values
                lon = tags["GPS GPSLongitude"].values
                lat_ref = tags.get("GPS GPSLatitudeRef", "N").values[0]
                lon_ref = tags.get("GPS GPSLongitudeRef", "E").values[0]

                lat = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
                lon = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600
                if lat_ref == "S":
                    lat = -lat
                if lon_ref == "W":
                    lon = -lon

                return lat, lon
        except Exception as e:
            logging.warning(f"照片 {photo_path} 提取GPS信息失败: {str(e)}")
            return None
    else:
        # 对于HEIC文件，使用PIL和pillow_heif处理
        try:
            from pillow_heif import read_heif
            from PIL import Image
            
            # 使用pillow_heif读取HEIC文件
            heif_file = read_heif(photo_path)
            pil_image = heif_file.to_pillow()
            
            # 获取EXIF数据
            exif_data = pil_image.getexif()
            
            if exif_data:
                # 直接检查EXIF数据中是否包含GPS信息
                gps_info = exif_data.get_ifd(34853)  # GPSInfo IFD
                if gps_info:
                    try:
                        # 解析GPS信息
                        lat_ref = gps_info.get(1)  # GPSLatitudeRef
                        lon_ref = gps_info.get(3)  # GPSLongitudeRef
                        lat = gps_info.get(2)      # GPSLatitude
                        lon = gps_info.get(4)      # GPSLongitude
                        
                        if lat_ref and lon_ref and lat and lon:
                            # 转换为十进制格式
                            # 处理IFDRational对象
                            def rational_to_float(rational):
                                if hasattr(rational, 'numerator') and hasattr(rational, 'denominator'):
                                    return float(rational.numerator) / float(rational.denominator)
                                elif isinstance(rational, (tuple, list)) and len(rational) >= 2:
                                    return float(rational[0]) / float(rational[1])
                                else:
                                    return float(rational)
                            
                            lat_decimal = rational_to_float(lat[0]) + rational_to_float(lat[1]) / 60 + rational_to_float(lat[2]) / 3600
                            lon_decimal = rational_to_float(lon[0]) + rational_to_float(lon[1]) / 60 + rational_to_float(lon[2]) / 3600
                            
                            if isinstance(lat_ref, bytes):
                                lat_ref = lat_ref.decode('utf-8')
                            if isinstance(lon_ref, bytes):
                                lon_ref = lon_ref.decode('utf-8')
                                
                            if lat_ref == "S":
                                lat_decimal = -lat_decimal
                            if lon_ref == "W":
                                lon_decimal = -lon_decimal
                                
                            return lat_decimal, lon_decimal
                    except Exception as parse_error:
                        logging.warning(f"解析HEIC文件GPS信息时出错 {photo_path}: {str(parse_error)}")
                
                # 如果上面方法失败，尝试通过临时JPEG文件方式
                try:
                    import piexif
                    # 先将HEIC转换为JPEG临时文件
                    temp_jpg = os.path.join(os.path.dirname(photo_path), "temp_convert.jpg")
                    pil_image.save(temp_jpg, "JPEG", quality=95)
                    
                    # 使用piexif读取GPS信息
                    exif_dict = piexif.load(temp_jpg)
                    if "GPS" in exif_dict and exif_dict["GPS"]:
                        gps_data = exif_dict["GPS"]
                        
                        # 解析GPS信息
                        if 1 in gps_data and 2 in gps_data and 3 in gps_data and 4 in gps_data:
                            lat_ref = gps_data[1].decode('utf-8') if isinstance(gps_data[1], bytes) else gps_data[1]
                            lon_ref = gps_data[3].decode('utf-8') if isinstance(gps_data[3], bytes) else gps_data[3]
                            lat = gps_data[2]
                            lon = gps_data[4]
                            
                            # 转换为十进制格式
                            lat_decimal = float(lat[0][0]) / float(lat[0][1]) + float(lat[1][0]) / float(lat[1][1]) / 60 + float(lat[2][0]) / float(lat[2][1]) / 3600
                            lon_decimal = float(lon[0][0]) / float(lon[0][1]) + float(lon[1][0]) / float(lon[1][1]) / 60 + float(lon[2][0]) / float(lon[2][1]) / 3600
                            
                            # 删除临时文件
                            os.remove(temp_jpg)
                            
                            if lat_ref == "S":
                                lat_decimal = -lat_decimal
                            if lon_ref == "W":
                                lon_decimal = -lon_decimal
                                
                            return lat_decimal, lon_decimal
                    
                    # 删除临时文件
                    if os.path.exists(temp_jpg):
                        os.remove(temp_jpg)
                except Exception as piexif_error:
                    logging.warning(f"使用piexif处理HEIC文件GPS信息时出错 {photo_path}: {str(piexif_error)}")
                    # 删除可能存在的临时文件
                    temp_jpg = os.path.join(os.path.dirname(photo_path), "temp_convert.jpg")
                    if os.path.exists(temp_jpg):
                        os.remove(temp_jpg)
            else:
                logging.warning(f"HEIC照片 {photo_path} 没有EXIF数据")
                
            logging.warning(f"HEIC照片 {photo_path} 没有GPS信息")
            return None
        except Exception as e:
            logging.warning(f"处理HEIC文件 {photo_path} GPS信息失败: {str(e)}")
            return None

def get_photo_date(photo_path):
    """从照片中提取拍摄日期"""
    # 检查是否为HEIC文件
    is_heic = photo_path.lower().endswith('.heic')
    
    # 首先尝试使用exifread处理（非HEIC文件）
    if not is_heic:
        try:
            with open(photo_path, "rb") as f:
                tags = exifread.process_file(f)
                if "EXIF DateTimeOriginal" in tags:
                    date_str = str(tags["EXIF DateTimeOriginal"])
                    try:
                        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        logging.error(f"拍摄日期格式错误: {date_str}")
                        return None
                logging.warning(f"照片 {photo_path} 无拍摄日期")
                return None
        except Exception as e:
            logging.warning(f"照片 {photo_path} 提取拍摄日期失败: {str(e)}")
            return None
    else:
        # 对于HEIC文件，使用PIL和pillow_heif处理
        try:
            from pillow_heif import read_heif
            from PIL.ExifTags import TAGS
            from PIL import Image
            
            # 使用pillow_heif读取HEIC文件
            heif_file = read_heif(photo_path)
            pil_image = heif_file.to_pillow()
            
            # 获取EXIF数据
            exif_data = dict(pil_image.getexif())
            
            if exif_data:
                # 查找拍摄日期
                datetime_original = exif_data.get(306) or exif_data.get(36867)  # DateTime or DateTimeOriginal
                if datetime_original:
                    try:
                        dt = datetime.strptime(str(datetime_original), "%Y:%m:%d %H:%M:%S")
                        return dt
                    except Exception as e:
                        logging.error(f"解析HEIC照片 {photo_path} 拍摄日期时出错: {str(e)}, 日期字符串: {datetime_original}")
                else:
                    logging.warning(f"HEIC照片 {photo_path} 无拍摄日期信息")
            else:
                logging.warning(f"HEIC照片 {photo_path} 没有EXIF数据")
            return None
        except Exception as e:
            logging.warning(f"处理HEIC文件 {photo_path} 拍摄日期失败: {str(e)}")
            return None

def create_thumbnail(photo_path, temp_dir, base_dir, thumbnail_size=(500, 500)):
    """创建缩略图并返回保存路径，保持原始比例并自动旋转"""
    # 检查是否为HEIC文件
    is_heic = photo_path.lower().endswith('.heic')
    
    # 为每个源文件夹创建子目录，避免文件名冲突
    folder_name = os.path.basename(os.path.dirname(photo_path)) if os.path.dirname(photo_path) else "root"
    
    # 对于HEIC文件，创建专门的转换目录
    if is_heic:
        # HEIC文件转换后的JPG放在unified_photo_temp_heic文件夹中
        target_dir = os.path.join(temp_dir + "_heic", folder_name)
        file_name = os.path.basename(photo_path)
        converted_file_name = file_name.rsplit('.', 1)[0] + '.jpg'
        converted_photo_path = os.path.join(target_dir, converted_file_name)
        # 缩略图文件名使用.jpg后缀
        thumbnail_file_name = f"thumb_{file_name.rsplit('.', 1)[0]}.jpg"
    else:
        # 非HEIC文件的缩略图放在unified_photo_temp文件夹中
        target_dir = os.path.join(temp_dir, folder_name)
        file_name = os.path.basename(photo_path)
        # 确保缩略图文件名使用.jpg后缀
        if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
            name_without_ext = file_name.rsplit('.', 1)[0]
            thumbnail_file_name = f"thumb_{name_without_ext}.jpg"
        else:
            thumbnail_file_name = f"thumb_{file_name}.jpg"
    
    # 创建子目录结构
    os.makedirs(target_dir, exist_ok=True)
    
    thumbnail_path = os.path.join(target_dir, thumbnail_file_name)
    # 检查缩略图是否存在且格式正确
    if os.path.exists(thumbnail_path):
        # 验证文件扩展名是否正确
        if thumbnail_path.lower().endswith('.jpg'):
            logging.info(f"缩略图已存在: {thumbnail_path}")
            with Image.open(thumbnail_path) as img:
                # 保持原始宽高比
                width, height = img.size
                aspect_ratio = width / height
                max_width, max_height = thumbnail_size
                if aspect_ratio > 1:
                    new_width = min(max_width, width)
                    new_height = int(new_width / aspect_ratio)
                else:
                    new_height = min(max_height, height)
                    new_width = int(new_height * aspect_ratio)
                return thumbnail_path, new_width, new_height
        else:
            # 如果扩展名不正确，删除错误的文件
            logging.warning(f"缩略图扩展名不正确，删除文件: {thumbnail_path}")
            os.remove(thumbnail_path)

    # 初始化new_width和new_height变量
    new_width, new_height = thumbnail_size

    try:
        # 对于HEIC文件，先转换为JPEG格式
        if is_heic:
            # 如果转换后的JPEG文件不存在，则进行转换
            if not os.path.exists(converted_photo_path):
                # 使用pillow_heif读取HEIC文件
                from pillow_heif import read_heif
                heif_file = read_heif(photo_path)
                pil_image = heif_file.to_pillow()
                
                # 获取原始EXIF数据
                original_exif = pil_image.info.get('exif')
                if original_exif:
                    # 保存为JPEG格式并保留EXIF数据
                    pil_image.save(converted_photo_path, "JPEG", quality=95, exif=original_exif)
                    logging.info(f"HEIC文件已转换为JPEG并保留EXIF数据: {converted_photo_path}")
                else:
                    # 尝试从HEIF文件获取EXIF数据
                    try:
                        import piexif
                        temp_jpg = os.path.join(os.path.dirname(photo_path), "temp_exif.jpg")
                        pil_image.save(temp_jpg, "JPEG", quality=95)
                        with Image.open(temp_jpg) as temp_img:
                            temp_exif = temp_img.info.get('exif')
                        if temp_exif:
                            pil_image.save(converted_photo_path, "JPEG", quality=95, exif=temp_exif)
                            logging.info(f"HEIC文件已转换为JPEG并保留EXIF数据: {converted_photo_path}")
                        else:
                            pil_image.save(converted_photo_path, "JPEG", quality=95)
                            logging.info(f"HEIC文件已转换为JPEG（无EXIF数据）: {converted_photo_path}")
                        os.remove(temp_jpg)
                    except Exception as e:
                        logging.warning(f"提取EXIF数据失败: {str(e)}")
                        pil_image.save(converted_photo_path, "JPEG", quality=95)
                        logging.info(f"HEIC文件已转换为JPEG: {converted_photo_path}")
            
            # 使用转换后的JPEG文件创建缩略图
            photo_path_to_use = converted_photo_path
        else:
            photo_path_to_use = photo_path

        # 使用PIL打开图像
        with Image.open(photo_path_to_use) as img:
            # 获取EXIF数据
            exif_data = None
            orientation = 1  # 默认方向
            orientation_tag = None
            
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                # 查找Orientation标签
                for tag_id in ExifTags.TAGS:
                    if ExifTags.TAGS[tag_id] == 'Orientation':
                        orientation_tag = tag_id
                        break
                
                if orientation_tag in exif:
                    orientation = exif[orientation_tag]
                
                # 保存EXIF数据以便后续使用
                exif_data = img.info.get('exif')
            
            logging.info(f"处理图像: {photo_path_to_use}, 原始方向: {orientation}")
            
            # 根据EXIF方向标签旋转图像
            # 参考: http://sylvana.net/jpegcrop/exif_orientation.html
            if orientation == 1:  # 正常方向
                pass
            elif orientation == 2:  # 水平翻转
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:  # 旋转180度
                img = img.transpose(Image.ROTATE_180)
            elif orientation == 4:  # 垂直翻转
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            elif orientation == 5:  # 顺时针旋转90度后垂直翻转
                # 正确处理方向5：先顺时针旋转90度，然后垂直翻转
                img = img.transpose(Image.ROTATE_90)
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            elif orientation == 6:  # 顺时针旋转90度
                img = img.transpose(Image.ROTATE_270)
            elif orientation == 7:  # 顺时针旋转90度后水平翻转
                img = img.transpose(Image.ROTATE_90)
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 8:  # 逆时针旋转90度
                img = img.transpose(Image.ROTATE_90)
            
            # 保持原始宽高比
            width, height = img.size
            aspect_ratio = width / height
            max_width, max_height = thumbnail_size
            if aspect_ratio > 1:
                new_width = min(max_width, width)
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = min(max_height, height)
                new_width = int(new_height * aspect_ratio)
                new_width = int(new_height * aspect_ratio)
            
            # 创建缩略图
            img.thumbnail((new_width, new_height), Image.LANCZOS)
            
            # 保存缩略图，保留EXIF数据（除了方向信息，因为我们已经应用了旋转）
            if exif_data:
                # 创建一个新的EXIF数据，将方向设置为1（正常方向）
                try:
                    exif_dict = piexif.load(exif_data)
                    if "0th" in exif_dict and orientation_tag in exif_dict["0th"]:
                        exif_dict["0th"][orientation_tag] = 1
                    exif_bytes = piexif.dump(exif_dict)
                    img.save(thumbnail_path, "JPEG", exif=exif_bytes, quality=90)
                except (ImportError, NameError, ValueError) as e:
                    # 如果没有piexif库或处理EXIF数据出错，则不修改EXIF数据
                    logging.warning(f"处理EXIF数据时出错: {str(e)}")
                    img.save(thumbnail_path, "JPEG", quality=90)
            else:
                img.save(thumbnail_path, "JPEG", quality=90)
            
            logging.info(f"创建缩略图: {thumbnail_path} ({new_width}x{new_height}), 原始方向: {orientation}")
            
            # 返回缩略图路径和尺寸
            return thumbnail_path, new_width, new_height
                
    except Exception as e:
        logging.error(f"创建缩略图失败: {photo_path}, 错误: {str(e)}")
        # 如果处理失败，返回原始图像路径和尺寸
        try:
            with Image.open(photo_path) as img:
                return photo_path, img.size[0], img.size[1]
        except:
            return photo_path, 100, 100  # 默认尺寸

def process_photo(photo_path, temp_dir, base_dir, thumbnail_size=(500, 500)):
    """处理单张照片，返回照片信息"""
    # 检查是否为HEIC文件
    is_heic = photo_path.lower().endswith('.heic')
    
    # 获取GPS信息（可以为None）
    gps_info = get_gps_info(photo_path)
    
    # 如果没有GPS信息，直接返回None，跳过处理
    if not gps_info:
        logging.info(f"跳过处理照片 {photo_path}：没有GPS坐标信息")
        return None
    
    lat, lon = gps_info
    
    # 验证坐标是否为有效数字
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        logging.warning(f"跳过处理照片 {photo_path}：坐标不是有效数字 (纬度: {lat}, 经度: {lon})")
        return None
    # 验证坐标是否在合理范围内
    elif not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        logging.warning(f"跳过处理照片 {photo_path}：坐标异常 (纬度: {lat}, 经度: {lon})")
        return None
    # 检查是否为明显的无效坐标（如全0坐标）
    elif lat == 0 and lon == 0:
        logging.warning(f"跳过处理照片 {photo_path}：坐标为零值 (纬度: {lat}, 经度: {lon})")
        return None
    # 检查是否为非常接近零的坐标（可能是无效数据）
    elif abs(lat) < 1e-6 and abs(lon) < 1e-6:
        logging.warning(f"跳过处理照片 {photo_path}：坐标接近零值 (纬度: {lat}, 经度: {lon})")
        return None
    
    # 转换坐标
    gcj_lng, gcj_lat = wgs84_to_gcj02(lon, lat)
    # 验证转换后的坐标是否有效
    if gcj_lat is None or gcj_lng is None or not isinstance(gcj_lat, (int, float)) or not isinstance(gcj_lng, (int, float)):
        logging.warning(f"跳过处理照片 {photo_path}：坐标转换失败 (纬度: {lat} -> {gcj_lat}, 经度: {lon} -> {gcj_lng})")
        return None

    # 创建缩略图
    thumbnail_path, thumb_width, thumb_height = create_thumbnail(photo_path, temp_dir, base_dir, thumbnail_size)
    
    # 处理照片路径（对于HEIC文件，使用转换后的JPEG文件路径）
    if is_heic:
        # HEIC文件转换后的JPG放在unified_photo_temp_heic文件夹中
        folder_name = os.path.basename(os.path.dirname(photo_path)) if os.path.dirname(photo_path) else "root"
        file_name = os.path.basename(photo_path)
        converted_file_name = file_name.rsplit('.', 1)[0] + '.jpg'
        converted_photo_path = os.path.join("unified_photo_temp_heic", folder_name, converted_file_name)
        # 确保路径使用正斜杠并相对于base_dir
        try:
            relative_photo_path = os.path.relpath(converted_photo_path, base_dir).replace("\\", "/")
        except ValueError:
            # 跨磁盘情况，使用绝对路径
            relative_photo_path = "file:///" + os.path.abspath(converted_photo_path).replace("\\", "/")
    else:
        # 非HEIC文件直接使用原始照片的绝对路径
        absolute_photo_path = os.path.abspath(photo_path).replace("\\", "/")
        relative_photo_path = "file:///" + absolute_photo_path
    
    # 处理缩略图路径
    # 所有缩略图都放在unified_photo_temp文件夹中
    try:
        relative_thumbnail_path = os.path.relpath(thumbnail_path, base_dir).replace("\\", "/")
    except ValueError:
        # 跨磁盘情况，使用绝对路径
        relative_thumbnail_path = "file:///" + os.path.abspath(thumbnail_path).replace("\\", "/")

    # 获取拍摄日期
    photo_date = get_photo_date(photo_path)
    if photo_date:
        photo_date_str = photo_date.strftime("%Y年%m月%d日 %H时%M分")
    else:
        photo_date_str = "未知日期"

    return {
        "latitude": gcj_lat,
        "longitude": gcj_lng,
        "photo_path": relative_photo_path,
        "thumbnail_path": relative_thumbnail_path,
        "photo_date": photo_date_str,
        "thumb_width": thumb_width,
        "thumb_height": thumb_height,
        "shoot_time": photo_date  # 添加 shoot_time 字段用于排序
    }