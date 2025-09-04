import sys
import json
import logging
import os
import time
from pathlib import Path

# 检查Python版本
if sys.version_info < (3, 8):
    print("错误: 需要Python 3.8或更高版本")
    print(f"当前版本: {sys.version}")
    input("按回车键退出...")
    sys.exit(1)

# 检查并导入必需模块
try:
    import requests
    import re
    import pandas as pd
    import base64
    import shutil
    import datetime
except ImportError as e:
    print(f"缺少必需的模块: {e}")
    print("请运行以下命令安装:")
    print("pip install requests pandas")
    input("按回车键退出...")
    sys.exit(1)
# 检查并导入PyQt6
try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton,
                                QFileDialog, QListWidget, QTableWidget, QTableWidgetItem, 
                                QHeaderView, QDialog, QTextEdit, QComboBox, QCheckBox, QListWidgetItem,
                                QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox,
                                QSplitter, QPlainTextEdit, QGroupBox, QGridLayout, QScrollArea,
                                QFrame, QProgressBar, QTabWidget, QAbstractItemView, QStyledItemDelegate, QStyle,
                                QSizePolicy)
    from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, QObject, QTimer, QSize, QUrl, QMimeData
    from PyQt6.QtGui import QPixmap, QImage, QFont, QPalette, QColor, QIcon, QTextOption, QDragEnterEvent, QDropEvent
except ImportError as e:
    print(f"缺少PyQt6模块: {e}")
    print("请运行以下命令安装:")
    print("pip install PyQt6")
    input("按回车键退出...")
    sys.exit(1)

# 导入声音播放模块
try:
    import winsound  # Windows系统声音
except ImportError:
    winsound = None

try:
    import subprocess  # 跨平台声音播放
except ImportError:
    subprocess = None

def get_app_path():
    """获取应用程序路径，支持打包后的exe"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent

APP_PATH = get_app_path()
IMAGES_PATH = APP_PATH / 'images'

def ensure_images_directory():
    """确保images目录存在"""
    if not IMAGES_PATH.exists():
        IMAGES_PATH.mkdir(parents=True, exist_ok=True)
        logging.info(f"创建图片目录: {IMAGES_PATH}")

def create_category_directory(category_name):
    """创建分类目录"""
    ensure_images_directory()
    category_path = IMAGES_PATH / category_name
    if not category_path.exists():
        category_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"创建分类目录: {category_path}")
    return category_path

class DragDropTableWidget(QTableWidget):
    """支持拖拽的表格组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = None
        
    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否为图片文件
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        event.acceptProposedAction()
                        return
        event.ignore()
    
    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """放下事件"""
        if event.mimeData().hasUrls() and self.main_window:
            urls = event.mimeData().urls()
            image_files = []
            
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        image_files.append(file_path)
            
            if image_files:
                # 获取放下位置的行索引
                drop_row = self.rowAt(event.position().toPoint().y())
                if drop_row == -1:
                    # 如果拖拽到空白区域，创建新行
                    drop_row = len(self.main_window.prompt_table_data)
                
                # 调用主窗口的处理方法
                self.main_window.handle_image_drop(image_files, drop_row)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

def rename_category_directory(old_name, new_name):
    """重命名分类目录"""
    ensure_images_directory()
    old_path = IMAGES_PATH / old_name
    new_path = IMAGES_PATH / new_name
    
    if old_path.exists() and not new_path.exists():
        old_path.rename(new_path)
        logging.info(f"重命名分类目录: {old_path} -> {new_path}")
    elif not old_path.exists():
        # 如果旧目录不存在，创建新目录
        create_category_directory(new_name)

def delete_category_directory(category_name):
    """删除分类目录及其所有内容"""
    ensure_images_directory()
    category_path = IMAGES_PATH / category_name
    if category_path.exists():
        shutil.rmtree(category_path)
        logging.info(f"删除分类目录: {category_path}")

def copy_image_to_category(source_path, category_name, image_name):
    """复制图片到分类目录"""
    try:
        # 验证输入参数
        if not source_path or not category_name or not image_name:
            raise ValueError("源路径、分类名和图片名不能为空")
        
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"源图片文件不存在: {source_path}")
        
        # 验证图片名称，移除非法字符
        safe_image_name = "".join(c for c in image_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_image_name:
            safe_image_name = "image"
            
        # 创建分类目录
        category_path = create_category_directory(category_name)
        
        # 获取文件扩展名
        source_ext = source_path.suffix.lower()
        if not source_ext or source_ext not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
            source_ext = '.png'  # 默认扩展名
        
        # 构建目标文件路径，避免文件名冲突
        target_filename = f"{safe_image_name}{source_ext}"
        target_path = category_path / target_filename
        
        # 如果文件已存在，添加数字后缀
        counter = 1
        while target_path.exists():
            target_filename = f"{safe_image_name}_{counter}{source_ext}"
            target_path = category_path / target_filename
            counter += 1
        
        # 复制文件
        shutil.copy2(source_path, target_path)
        logging.info(f"复制图片: {source_path} -> {target_path}")
        
        # 验证复制结果
        if not target_path.exists():
            raise RuntimeError(f"图片复制失败，目标文件不存在: {target_path}")
        
        # 返回相对路径
        return f"images/{category_name}/{target_filename}"
        
    except Exception as e:
        logging.error(f"复制图片到分类目录失败: {e}", exc_info=True)
        raise

def image_to_base64(image_path):
    """将图片文件转换为base64编码"""
    try:
        with open(image_path, 'rb') as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            # 根据文件扩展名确定MIME类型
            ext = Path(image_path).suffix.lower()
            if ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext == '.png':
                mime_type = 'image/png'
            elif ext == '.gif':
                mime_type = 'image/gif'
            elif ext == '.webp':
                mime_type = 'image/webp'
            else:
                mime_type = 'image/png'  # 默认
            
            return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        logging.error(f"转换图片为base64失败: {e}")
        return None

# 配置日志
logging.basicConfig(
    filename=APP_PATH / 'sora_generator.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# 缩略图缓存目录
THUMBNAIL_CACHE_PATH = APP_PATH / 'thumbnails'

# 样式缓存，避免重复解析CSS
_CACHED_MODERN_STYLE = None

def ensure_thumbnail_cache_directory():
    """确保缩略图缓存目录存在"""
    if not THUMBNAIL_CACHE_PATH.exists():
        THUMBNAIL_CACHE_PATH.mkdir(parents=True, exist_ok=True)
        logging.info(f"创建缩略图缓存目录: {THUMBNAIL_CACHE_PATH}")

def get_thumbnail_cache_path(image_path):
    """获取缩略图缓存路径"""
    ensure_thumbnail_cache_directory()
    # 使用图片路径的hash作为缓存文件名
    import hashlib
    path_hash = hashlib.md5(str(image_path).encode()).hexdigest()
    return THUMBNAIL_CACHE_PATH / f"{path_hash}.jpg"

def create_thumbnail(image_path, thumbnail_path, size=(120, 120)):
    """创建并缓存缩略图"""
    try:
        if not os.path.exists(image_path):
            return None
            
        # 加载原图
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return None
        
        # 创建缩略图
        thumbnail = pixmap.scaled(
            size[0], size[1], 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 保存缩略图到缓存
        thumbnail.save(str(thumbnail_path), "JPEG", 85)
        return thumbnail
        
    except Exception as e:
        logging.error(f"创建缩略图失败 {image_path}: {str(e)}")
        return None

def get_cached_thumbnail(image_path, size=(120, 120)):
    """获取缓存的缩略图，如果不存在则创建"""
    thumbnail_path = get_thumbnail_cache_path(image_path)
    
    # 检查缓存是否存在且是最新的
    if thumbnail_path.exists():
        try:
            # 检查原图是否比缓存更新
            if os.path.exists(image_path):
                original_time = os.path.getmtime(image_path)
                cache_time = os.path.getmtime(thumbnail_path)
                
                if cache_time >= original_time:
                    # 缓存是最新的，直接加载
                    return QPixmap(str(thumbnail_path))
        except Exception:
            pass
    
    # 创建新的缩略图
    return create_thumbnail(image_path, thumbnail_path, size)

class WorkerSignals(QObject):
    finished = pyqtSignal(str, str, str)  # 提示词, 图片URL, 编号
    error = pyqtSignal(str, str)     # 提示词, 错误信息
    progress = pyqtSignal(str, str)  # 提示词, 状态信息

class Worker(QRunnable):
    def __init__(self, prompt, api_key, image_data=None, api_platform="云雾", image_model="sora", retry_count=3, number=None):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key
        self.image_data = image_data or []  # 现在包含{'name': '', 'url': '', 'path': ''} 的数据
        self.api_platform = api_platform
        self.image_model = image_model  # 添加生图模型参数
        self.retry_count = retry_count
        self.number = number
        self.signals = WorkerSignals()
        
    def run(self):
        try:
            # 发送进度信号
            self.signals.progress.emit(self.prompt, "生成中...")
            
            # 验证API密钥
            if not self.api_key:
                raise ValueError("API密钥不能为空")
                
            # 构建API请求
            if self.api_platform == "云雾":
                api_url = "https://yunwu.ai/v1/chat/completions"
            elif self.api_platform == "apicore":
                api_url = "https://api.apicore.ai/v1/chat/completions"
            else:
                api_url = "https://api.apicore.ai/v1/chat/completions"  # 默认使用apicore
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 构建消息内容
            content = [{"type": "text", "text": self.prompt}]
            
            # 添加图片（支持URL、本地文件和base64数据）
            for img_data in self.image_data:
                if 'data' in img_data and img_data['data']:
                    # 直接使用base64数据（拖拽参考图）
                    base64_url = f"data:image/png;base64,{img_data['data']}"
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": base64_url}
                    })
                    logging.info(f"添加拖拽参考图片: {img_data['name']} (base64数据)")
                elif 'path' in img_data and img_data['path']:
                    # 本地图片，转换为base64
                    local_path = APP_PATH / img_data['path']
                    if local_path.exists():
                        base64_url = image_to_base64(local_path)
                        if base64_url:
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": base64_url}
                            })
                            logging.info(f"添加本地图片: {img_data['name']} -> {img_data['path']}")
                        else:
                            logging.warning(f"本地图片转换base64失败: {img_data['path']}")
                    else:
                        logging.warning(f"本地图片文件不存在: {img_data['path']}")
                elif 'url' in img_data and img_data['url']:
                    # 网络图片，使用URL
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": img_data['url']}
                    })
                    logging.info(f"添加网络图片: {img_data['name']} -> {img_data['url']}")
            
            # 根据选择的模型设置API参数
            if self.image_model == "sora":
                # Sora模型配置
                if self.api_platform == "云雾":
                    model = "sora"  # 修正：云雾平台使用 sora 而不是 sora_image
                elif self.api_platform == "apicore":
                    model = "sora"
                else:
                    model = "sora"
            elif self.image_model == "nano-banana":
                # nano-banana模型配置
                if self.api_platform == "云雾":
                    model = "fal-ai/nano-banana"
                elif self.api_platform == "apicore":
                    model = "fal-ai/nano-banana"  # 修正：统一使用 fal-ai/nano-banana
                else:
                    model = "fal-ai/nano-banana"
            else:
                # 默认使用sora
                model = "sora"
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an AI image generator. Generate high-quality images based on user text descriptions. Always provide the generated image URL in the response."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "max_tokens": 1000,  # 添加max_tokens限制
                "temperature": 0.7   # 添加适中的创造性
            }
            
            # 记录请求信息
            logging.info("发送API请求:")
            logging.info(f"URL: {api_url}")
            logging.info(f"请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            # 发送请求(带重试机制)
            retry_times = 0
            while retry_times <= self.retry_count:
                try:
                    # 添加随机延迟，避免同时发送大量请求
                    import random
                    # 初次请求延迟较短，重试时延迟会递增
                    initial_delay = random.uniform(0.5, 1.5)
                    time.sleep(initial_delay)
                    
                    response = requests.post(
                        api_url, 
                        headers=headers, 
                        json=payload,
                        timeout=300  # 减少超时时间到5分钟，避免长时间挂起
                    )
                    
                    # 记录响应信息
                    logging.info(f"API响应状态码: {response.status_code}")
                    logging.info(f"API响应内容: {response.text}")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # 解析响应
                    # 平台返回文本中的图片URL
                    content = data["choices"][0]["message"]["content"]
                    
                    # 尝试多种格式的图片URL，按优先级排序
                    image_url_match = None
                    
                    # 优先级1: 点击下载链接
                    image_url_match = re.search(r'\[点击下载\]\((.*?)\)', content)
                    
                    # 优先级2: 图片markdown格式
                    if not image_url_match:
                        image_url_match = re.search(r'!\[图片\]\((.*?)\)', content)
                    
                    # 优先级3: 任何markdown图片格式
                    if not image_url_match:
                        image_url_match = re.search(r'!\[.*?\]\((https?://[^\)]+)\)', content)
                    
                    # 优先级4: 直接查找图片URL（常见格式）
                    if not image_url_match:
                        image_url_match = re.search(r'(https?://[^\s\)\]]+\.(?:jpg|jpeg|png|gif|webp|bmp))', content, re.IGNORECASE)
                    
                    # 优先级5: 查找任何以http开头的链接（可能是图片）
                    if not image_url_match:
                        image_url_match = re.search(r'(https?://[^\s\)\]]+)', content)
                    
                    if image_url_match:
                        image_url = image_url_match.group(1)
                    else:
                        error_msg = f"响应中没有找到图片URL。响应内容: {content}"
                        logging.error(error_msg)
                        raise ValueError(error_msg)
                    
                    logging.info(f"成功提取图片URL: {image_url}")
                    self.signals.finished.emit(self.prompt, image_url, self.number or "")
                    return
                        
                except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                    retry_times += 1
                    error_detail = f"API平台: {self.api_platform}, 模型: {model}, 错误: {str(e)}"
                    
                    if hasattr(e, 'response') and e.response is not None:
                        error_detail += f", 状态码: {e.response.status_code}, 响应: {e.response.text[:500]}"
                    
                    if retry_times <= self.retry_count:
                        logging.warning(f"请求失败,正在进行第{retry_times}次重试: {error_detail}")
                        self.signals.progress.emit(self.prompt, f"重试中 ({retry_times}/{self.retry_count})...")
                        # 递增式重试延迟：第1次重试等待30秒，第2次等待60秒，第3次等待90秒
                        retry_delay = 30 * retry_times
                        logging.info(f"重试延迟 {retry_delay} 秒...")
                        # 显示倒计时，让用户知道等待进度
                        for remaining in range(retry_delay, 0, -5):
                            self.signals.progress.emit(self.prompt, f"重试中 ({retry_times}/{self.retry_count}) - {remaining}秒后重试...")
                            time.sleep(5)
                        continue
                    else:
                        error_msg = f"请求失败(已重试{self.retry_count}次): {error_detail}"
                        logging.error(error_msg)
                        self.signals.error.emit(self.prompt, error_msg)
                        return
                        
        except Exception as e:
            error_msg = f"发生错误: {str(e)}"
            logging.error(error_msg)
            self.signals.error.emit(self.prompt, error_msg)

class SettingsDialog(QDialog):
    """统一设置管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_done = False  # 初始化标志
        self.setWindowTitle("⚙️ 设置管理中心")
        self.resize(1100, 750)
        self.setMinimumSize(900, 650)
        
        # 从父窗口获取数据
        if parent:
            self.api_key = parent.api_key
            self.api_platform = parent.api_platform
            self.image_model = parent.image_model  # 获取生图模型配置
            # 分离的API密钥
            self.sora_api_key = getattr(parent, 'sora_api_key', '')
            self.nano_api_key = getattr(parent, 'nano_api_key', '')
            self.thread_count = parent.thread_count
            self.retry_count = parent.retry_count
            self.save_path = parent.save_path
            self.image_ratio = parent.image_ratio
            self.style_library = parent.style_library.copy()
            self.category_links = parent.category_links.copy()
            self.current_style = parent.current_style
            self.custom_style_content = parent.custom_style_content
            # OpenRouter AI优化配置
            self.openrouter_api_key = getattr(parent, 'openrouter_api_key', '')
            self.ai_model = getattr(parent, 'ai_model', 'qwen/qwq-32b')
            self.meta_prompt = getattr(parent, 'meta_prompt', '')
            self.meta_prompt_template = getattr(parent, 'meta_prompt_template', 'template1')
            self.optimization_history = getattr(parent, 'optimization_history', [])
        else:
            self.api_key = ""
            self.api_platform = "云雾"
            self.image_model = "sora"  # 默认生图模型
            self.thread_count = 5
            self.retry_count = 3
            self.save_path = ""
            self.image_ratio = "3:2"
            self.style_library = {}
            self.category_links = {}
            self.current_style = ""
            self.custom_style_content = ""
            # OpenRouter AI优化配置默认值
            self.openrouter_api_key = ""
            self.ai_model = "qwen/qwq-32b"
            self.meta_prompt = ""
            self.meta_prompt_template = "template1"
            self.optimization_history = []
        
        self.setup_ui()
        self.load_settings()
        
        self._init_done = True  # 标记初始化完成
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 基础配置标签页
        self.create_config_tab()
        
        # 风格库管理标签页
        self.create_style_tab()
        
        # 参考图管理标签页
        self.create_image_tab()
        
        # AI优化配置标签页
        self.create_ai_optimize_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("✅ 确定")
        self.ok_button.clicked.connect(self.accept_settings)
        
        self.cancel_button = QPushButton("❌ 取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 设置现代化样式
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
            }
            
            QTabWidget::tab-bar {
                alignment: left;
            }
            
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #1976d2;
                color: #1976d2;
            }
            
            QTabBar::tab:hover {
                background-color: #e3f2fd;
            }
        """)
    
    def create_config_tab(self):
        """创建基础配置标签页"""
        config_widget = QWidget()
        layout = QVBoxLayout(config_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # API配置区域
        api_group = QGroupBox("🔑 API配置")
        api_layout = QGridLayout(api_group)
        
        # Sora模型API密钥
        api_layout.addWidget(QLabel("Sora模型API密钥:"), 0, 0)
        self.sora_api_input = QLineEdit()
        self.sora_api_input.setPlaceholderText("请输入Sora模型的API密钥...")
        self.sora_api_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.sora_api_input, 0, 1, 1, 2)
        
        # Sora密钥显示/隐藏按钮
        self.show_sora_key_button = QPushButton("显示")
        self.show_sora_key_button.setMaximumWidth(80)
        self.show_sora_key_button.clicked.connect(self.toggle_sora_key_visibility)
        api_layout.addWidget(self.show_sora_key_button, 0, 3)
        
        # nano-banana模型API密钥
        api_layout.addWidget(QLabel("Nano-banana模型API密钥:"), 1, 0)
        self.nano_api_input = QLineEdit()
        self.nano_api_input.setPlaceholderText("请输入nano-banana模型的API密钥...")
        self.nano_api_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.nano_api_input, 1, 1, 1, 2)
        
        # nano-banana密钥显示/隐藏按钮
        self.show_nano_key_button = QPushButton("显示")
        self.show_nano_key_button.setMaximumWidth(80)
        self.show_nano_key_button.clicked.connect(self.toggle_nano_key_visibility)
        api_layout.addWidget(self.show_nano_key_button, 1, 3)
        
        # 连接文本变化事件
        self.sora_api_input.textChanged.connect(self.on_sora_api_changed)
        self.nano_api_input.textChanged.connect(self.on_nano_api_changed)
        
        # API平台配置
        api_layout.addWidget(QLabel("API平台:"), 2, 0)
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["云雾", "apicore"])
        api_layout.addWidget(self.platform_combo, 2, 1)
        
        # 生图模型配置
        api_layout.addWidget(QLabel("生图模型:"), 3, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(["sora", "nano-banana"])
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        api_layout.addWidget(self.model_combo, 3, 1)
        
        # 测试连接按钮
        self.test_api_button = QPushButton("测试API连接")
        self.test_api_button.clicked.connect(self.test_api_connection)
        api_layout.addWidget(self.test_api_button, 3, 2)
        
        layout.addWidget(api_group)
        
        # 生成参数区域
        params_group = QGroupBox("⚡ 生成参数")
        params_layout = QGridLayout(params_group)
        
        params_layout.addWidget(QLabel("并发线程数:"), 0, 0)
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 2000)
        self.thread_spin.setSuffix(" 个")
        params_layout.addWidget(self.thread_spin, 0, 1)
        
        params_layout.addWidget(QLabel("失败重试次数:"), 0, 2)
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(1, 10)
        self.retry_spin.setSuffix(" 次")
        params_layout.addWidget(self.retry_spin, 0, 3)
        
        params_layout.addWidget(QLabel("保存路径:"), 1, 0)
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择图片保存路径...")
        params_layout.addWidget(self.path_input, 1, 1, 1, 2)
        
        path_button = QPushButton("浏览")
        path_button.clicked.connect(self.select_save_path)
        params_layout.addWidget(path_button, 1, 3)
        
        params_layout.addWidget(QLabel("图片比例:"), 2, 0)
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["1:1", "3:2", "4:3", "16:9", "9:16", "2:3", "3:4"])
        params_layout.addWidget(self.ratio_combo, 2, 1)
        
        layout.addWidget(params_group)
        
        # 使用说明
        tips_group = QGroupBox("💡 使用提示")
        tips_layout = QVBoxLayout(tips_group)
        
        tips_text = QLabel("""
        <b>API密钥配置:</b><br>
        • 分别为不同模型配置独立的API密钥<br>
        • 支持云雾和apicore两个平台<br>
        • 可点击"显示"按钮查看密钥内容<br><br>
        
        <b>生成参数说明:</b><br>
        • 线程数: 同时处理的图片数量，建议5-20<br>
        • 重试次数: 失败后自动重试的次数<br>
        • 图片比例: 生成图片的宽高比例
        """)
        tips_text.setWordWrap(True)
        tips_layout.addWidget(tips_text)
        
        layout.addWidget(tips_group)
        layout.addStretch()
        
        self.tab_widget.addTab(config_widget, "⚙️ 基础配置")
        
    def on_model_changed(self, model_name):
        """模型选择改变时更新主界面显示"""
        try:
            if hasattr(self, 'current_model_label'):
                self.current_model_label.setText(model_name)
                # 根据不同模型设置不同颜色
                if model_name == "sora":
                    color = "#17a2b8"  # 蓝色
                elif model_name == "nano-banana":
                    color = "#fd7e14"  # 橙色
                else:
                    color = "#6c757d"  # 默认灰色
                
                self.current_model_label.setStyleSheet(f"""
                    QLabel {{
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: bold;
                        background-color: {color};
                        border-radius: 8px;
                        padding: 6px 12px;
                        margin-left: 15px;
                    }}
                """)
        except Exception as e:
            print(f"模型显示更新失败: {e}")
            pass
    
    def create_style_tab(self):
        """创建风格库管理标签页"""
        style_widget = QWidget()
        layout = QVBoxLayout(style_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部操作区域
        top_layout = QHBoxLayout()
        
        # 风格选择
        top_layout.addWidget(QLabel("当前风格:"))
        self.style_combo = QComboBox()
        self.style_combo.setMinimumWidth(200)
        self.style_combo.addItem("选择风格...")
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        top_layout.addWidget(self.style_combo)
        
        top_layout.addStretch()
        
        # 快速操作按钮
        self.new_style_button = QPushButton("新建")
        self.copy_style_button = QPushButton("复制")
        self.delete_style_button = QPushButton("删除")
        
        self.new_style_button.clicked.connect(self.new_style)
        self.copy_style_button.clicked.connect(self.copy_style)
        self.delete_style_button.clicked.connect(self.delete_style)
        
        top_layout.addWidget(self.new_style_button)
        top_layout.addWidget(self.copy_style_button)
        top_layout.addWidget(self.delete_style_button)
        
        layout.addLayout(top_layout)
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：风格列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("风格列表"))
        self.style_list = QListWidget()
        self.style_list.setMinimumWidth(220)
        self.style_list.currentItemChanged.connect(self.on_style_list_changed)
        left_layout.addWidget(self.style_list)
        
        # 导入导出按钮
        io_layout = QHBoxLayout()
        self.import_style_button = QPushButton("导入")
        self.export_style_button = QPushButton("导出")
        self.reset_style_button = QPushButton("重置")
        
        self.import_style_button.clicked.connect(self.import_styles)
        self.export_style_button.clicked.connect(self.export_styles)
        self.reset_style_button.clicked.connect(self.reset_default_styles)
        
        io_layout.addWidget(self.import_style_button)
        io_layout.addWidget(self.export_style_button)
        io_layout.addWidget(self.reset_style_button)
        left_layout.addLayout(io_layout)
        
        # 右侧：风格编辑
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 风格名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("风格名称:"))
        self.style_name_input = QLineEdit()
        self.style_name_input.setPlaceholderText("请输入风格名称...")
        name_layout.addWidget(self.style_name_input)
        right_layout.addLayout(name_layout)
        
        # 风格内容
        right_layout.addWidget(QLabel("风格内容:"))
        self.style_content_edit = QPlainTextEdit()
        self.style_content_edit.setPlaceholderText("请输入风格描述内容...\n\n例如：\n极致的超写实主义照片风格，画面呈现出顶级数码单反相机的拍摄效果...")
        right_layout.addWidget(self.style_content_edit)
        
        # 字符计数和保存按钮
        bottom_layout = QHBoxLayout()
        self.style_char_count = QLabel("字符数: 0")
        self.style_char_count.setStyleSheet("color: #666;")
        bottom_layout.addWidget(self.style_char_count)
        
        bottom_layout.addStretch()
        
        self.save_style_button = QPushButton("保存风格")
        self.save_style_button.clicked.connect(self.save_current_style)
        bottom_layout.addWidget(self.save_style_button)
        
        right_layout.addLayout(bottom_layout)
        
        # 添加到分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([250, 550])
        
        layout.addWidget(main_splitter)
        
        # 绑定文本变化事件
        self.style_name_input.textChanged.connect(self.update_style_char_count)
        self.style_content_edit.textChanged.connect(self.update_style_char_count)
        self.style_content_edit.textChanged.connect(self.on_style_content_changed)
        
        self.current_style_name = ""
        self.tab_widget.addTab(style_widget, "🎨 风格库")
    
    def create_image_tab(self):
        """创建参考图管理标签页"""
        image_widget = QWidget()
        layout = QVBoxLayout(image_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部操作区域
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(QLabel("分类管理:"))
        
        self.new_category_button = QPushButton("新建分类")
        self.rename_category_button = QPushButton("重命名")
        self.delete_category_button = QPushButton("删除分类")
        
        self.new_category_button.clicked.connect(self.new_category)
        self.rename_category_button.clicked.connect(self.rename_category)
        self.delete_category_button.clicked.connect(self.delete_category)
        
        top_layout.addWidget(self.new_category_button)
        top_layout.addWidget(self.rename_category_button)
        top_layout.addWidget(self.delete_category_button)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # 主要内容区域
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：分类列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("图片分类"))
        self.category_list = QListWidget()
        self.category_list.setMinimumWidth(200)
        self.category_list.currentItemChanged.connect(self.on_category_changed)
        left_layout.addWidget(self.category_list)
        
        # 右侧：图片管理
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 图片操作按钮
        image_buttons_layout = QHBoxLayout()
        image_buttons_layout.addWidget(QLabel("图片管理:"))
        
        self.add_image_button = QPushButton("添加图片")
        self.delete_image_button = QPushButton("删除选中")
        
        self.add_image_button.clicked.connect(self.add_image)
        self.delete_image_button.clicked.connect(self.delete_image)
        
        image_buttons_layout.addWidget(self.add_image_button)
        image_buttons_layout.addWidget(self.delete_image_button)
        image_buttons_layout.addStretch()
        
        right_layout.addLayout(image_buttons_layout)
        
        # 图片列表表格
        self.image_table = QTableWidget()
        self.image_table.setColumnCount(2)
        self.image_table.setHorizontalHeaderLabels(["图片名称", "路径/链接"])
        self.image_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.image_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.image_table.cellChanged.connect(self.on_image_changed)
        self.image_table.cellDoubleClicked.connect(self.on_image_table_double_clicked)
        right_layout.addWidget(self.image_table)
        
        # 使用说明
        tips_layout = QVBoxLayout()
        tips_label = QLabel("""
<b>使用说明:</b><br>
• 点击"添加图片"选择本地图片文件，系统会自动复制到项目目录<br>
• 在提示词中包含图片名称，系统会自动添加对应的参考图<br>
• 建议每个提示词最多包含3-4张参考图<br>
• 支持本地图片（优先）和网络图片链接（兼容旧版本）
        """)
        tips_label.setWordWrap(True)
        tips_label.setStyleSheet("color: #666; background-color: #f8f9fa; padding: 10px; border-radius: 6px; font-size: 14px;")
        tips_layout.addWidget(tips_label)
        
        right_layout.addLayout(tips_layout)
        
        # 添加到分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([200, 600])
        
        layout.addWidget(main_splitter)
        
        self.current_category = ""
        self.tab_widget.addTab(image_widget, "🖼️ 参考图库")
    
    def create_ai_optimize_tab(self):
        """创建AI优化配置标签页"""
        ai_widget = QWidget()
        layout = QVBoxLayout(ai_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # OpenRouter API配置区域
        api_group = QGroupBox("🔑 OpenRouter API 配置")
        api_layout = QVBoxLayout(api_group)
        
        # API Key输入
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key:"))
        
        self.openrouter_key_input = QLineEdit()
        self.openrouter_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_key_input.setPlaceholderText("请输入OpenRouter API Key")
        key_layout.addWidget(self.openrouter_key_input)
        
        self.show_openrouter_key_button = QPushButton("显示")
        self.show_openrouter_key_button.clicked.connect(self.toggle_openrouter_key_visibility)
        key_layout.addWidget(self.show_openrouter_key_button)
        
        api_layout.addLayout(key_layout)
        
        # AI模型选择
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("AI模型:"))
        
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItems([
            "qwen/qwq-32b",
            "google/gemini-2.5-pro", 
            "deepseek/deepseek-chat-v3.1"
        ])
        model_layout.addWidget(self.ai_model_combo)
        model_layout.addStretch()
        
        api_layout.addLayout(model_layout)
        layout.addWidget(api_group)
        
        # 元提示词配置区域
        meta_group = QGroupBox("📝 元提示词配置")
        meta_layout = QVBoxLayout(meta_group)
        
        # 预设模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("预设模板:"))
        
        self.meta_template_combo = QComboBox()
        self.meta_template_combo.addItems([
            "生图提示词优化模板1",
            "生图提示词优化模板2"
        ])
        self.meta_template_combo.currentTextChanged.connect(self.on_template_changed)
        template_layout.addWidget(self.meta_template_combo)
        
        self.load_template_button = QPushButton("📥 加载模板")
        self.load_template_button.clicked.connect(self.load_meta_template)
        template_layout.addWidget(self.load_template_button)
        template_layout.addStretch()
        
        meta_layout.addLayout(template_layout)
        
        # 元提示词编辑区域
        meta_layout.addWidget(QLabel("元提示词内容:"))
        self.meta_prompt_text = QTextEdit()
        self.meta_prompt_text.setPlaceholderText("请输入或选择元提示词模板...")
        self.meta_prompt_text.setMinimumHeight(200)
        meta_layout.addWidget(self.meta_prompt_text)
        
        layout.addWidget(meta_group)
        
        # 优化历史记录区域
        history_group = QGroupBox("📊 优化历史记录")
        history_layout = QVBoxLayout(history_group)
        
        # 历史记录按钮
        history_buttons_layout = QHBoxLayout()
        self.view_history_button = QPushButton("查看历史")
        self.view_history_button.clicked.connect(self.view_optimization_history)
        self.clear_history_button = QPushButton("清空历史")
        self.clear_history_button.clicked.connect(self.clear_optimization_history)
        
        history_buttons_layout.addWidget(self.view_history_button)
        history_buttons_layout.addWidget(self.clear_history_button)
        history_buttons_layout.addStretch()
        
        history_layout.addLayout(history_buttons_layout)
        
        # 历史记录统计
        self.history_stats_label = QLabel("历史记录: 0 条")
        self.history_stats_label.setStyleSheet("color: #666; font-size: 14px;")
        history_layout.addWidget(self.history_stats_label)
        
        layout.addWidget(history_group)
        
        # 使用说明
        tips_layout = QVBoxLayout()
        tips_label = QLabel("""
<b>使用说明:</b><br>
• 在OpenRouter官网注册并获取API Key<br>
• 选择适合的AI模型进行提示词优化<br>
• 元提示词用于指导AI如何优化你的生图提示词<br>
• 可使用预设模板或自定义元提示词<br>
• 所有优化记录都会保存在历史中供查看
        """)
        tips_label.setWordWrap(True)
        tips_label.setStyleSheet("color: #666; background-color: #f8f9fa; padding: 10px; border-radius: 6px; font-size: 14px;")
        tips_layout.addWidget(tips_label)
        
        layout.addLayout(tips_layout)
        layout.addStretch()
        
        self.tab_widget.addTab(ai_widget, "🤖 AI优化")
    
    def toggle_openrouter_key_visibility(self):
        """切换OpenRouter API密钥显示/隐藏"""
        if self.openrouter_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.openrouter_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_openrouter_key_button.setText("隐藏")
        else:
            self.openrouter_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_openrouter_key_button.setText("显示")
    
    def toggle_sora_key_visibility(self):
        """切换Sora模型API密钥显示/隐藏"""
        if self.sora_api_input.echoMode() == QLineEdit.EchoMode.Password:
            self.sora_api_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_sora_key_button.setText("隐藏")
        else:
            self.sora_api_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_sora_key_button.setText("显示")
    
    def toggle_nano_key_visibility(self):
        """切换Nano-banana模型API密钥显示/隐藏"""
        if self.nano_api_input.echoMode() == QLineEdit.EchoMode.Password:
            self.nano_api_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_nano_key_button.setText("隐藏")
        else:
            self.nano_api_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_nano_key_button.setText("显示")
    
    def get_current_api_key(self):
        """根据选择的模型获取对应的API密钥"""
        if self.image_model == "sora":
            return getattr(self, 'sora_api_key', '')
        elif self.image_model == "fal-ai/nano-banana":
            return getattr(self, 'nano_api_key', '')
        else:
            # 默认返回旧的API密钥以保持兼容性
            return getattr(self, 'api_key', '')
    
    def on_sora_api_changed(self, text):
        """Sora API密钥改变时的处理"""
        self.sora_api_key = text
        if hasattr(self, '_init_done') and self._init_done:  # 只有在初始化完成后才保存配置
            if self.parent():
                self.parent().sora_api_key = text
                self.parent().save_config()
    
    def on_nano_api_changed(self, text):
        """Nano-banana API密钥改变时的处理"""
        self.nano_api_key = text
        if hasattr(self, '_init_done') and self._init_done:  # 只有在初始化完成后才保存配置
            if self.parent():
                self.parent().nano_api_key = text
                self.parent().save_config()
    
    def on_template_changed(self):
        """模板选择改变时的处理"""
        self.load_meta_template()
    
    def load_meta_template(self):
        """加载预设元提示词模板"""
        template_name = self.meta_template_combo.currentText()
        
        templates = {
            "生图提示词优化模板1": """请优化以下AI绘图提示词，使其更加详细和专业：

要求：
1. 保持原始意图不变
2. 添加更多的视觉细节描述
3. 包含艺术风格、光线、色彩等元素
4. 使用专业的绘画术语
5. 确保提示词流畅自然

原始提示词：{original_prompt}

请直接输出优化后的提示词：""",
            
            "生图提示词优化模板2": """作为AI绘图专家，请将下面的提示词重写得更加精确和富有表现力：

优化方向：
- 增强画面构图和视角描述  
- 丰富材质和纹理细节
- 添加情感氛围营造
- 包含技术参数建议
- 保持简洁明了

待优化提示词：{original_prompt}

优化后的提示词："""
        }
        
        if template_name in templates:
            self.meta_prompt_text.setPlainText(templates[template_name])
    
    def view_optimization_history(self):
        """查看优化历史记录"""
        if not self.optimization_history:
            QMessageBox.information(self, "提示", "暂无优化历史记录")
            return
            
        # 创建历史记录查看窗口
        history_dialog = QDialog(self)
        history_dialog.setWindowTitle("🔍 优化历史记录")
        history_dialog.resize(800, 600)
        
        layout = QVBoxLayout(history_dialog)
        
        # 历史记录表格
        history_table = QTableWidget()
        history_table.setColumnCount(4)
        history_table.setHorizontalHeaderLabels(["时间", "原始提示词", "优化后提示词", "使用模型"])
        
        # 设置列宽
        header = history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # 填充数据
        history_table.setRowCount(len(self.optimization_history))
        for i, record in enumerate(self.optimization_history):
            history_table.setItem(i, 0, QTableWidgetItem(record.get('time', '')))
            history_table.setItem(i, 1, QTableWidgetItem(record.get('original', '')))
            history_table.setItem(i, 2, QTableWidgetItem(record.get('optimized', '')))
            history_table.setItem(i, 3, QTableWidgetItem(record.get('model', '')))
        
        layout.addWidget(history_table)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(history_dialog.accept)
        layout.addWidget(close_button)
        
        history_dialog.exec()
    
    def clear_optimization_history(self):
        """清空优化历史记录"""
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            "确定要清空所有优化历史记录吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.optimization_history.clear()
            self.update_history_stats()
            QMessageBox.information(self, "完成", "历史记录已清空")
    
    def update_history_stats(self):
        """更新历史记录统计"""
        count = len(self.optimization_history)
        self.history_stats_label.setText(f"历史记录: {count} 条")
    
    def toggle_key_visibility(self):
        """切换API密钥显示/隐藏"""
        if self.api_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_button.setText("隐藏")
        else:
            self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_button.setText("显示")
    
    def test_api_connection(self):
        """测试API连接"""
        api_key = self.api_input.text().strip()
        platform = self.platform_combo.currentText()
        image_model = self.model_combo.currentText()  # 获取选择的生图模型
        
        if not api_key:
            QMessageBox.warning(self, "错误", "请先输入API密钥")
            return
            
        # 禁用按钮，显示测试中
        self.test_api_button.setEnabled(False)
        self.test_api_button.setText("测试中...")
        
        # 构建测试请求
        try:
            # 构建API URL
            if platform == "云雾":
                api_url = "https://yunwu.ai/v1/chat/completions"
            elif platform == "apicore":
                api_url = "https://api.apicore.ai/v1/chat/completions"
            else:
                api_url = "https://api.apicore.ai/v1/chat/completions"  # 默认使用apicore
            
            # 根据选择的模型设置API参数（与Worker类保持一致）
            if image_model == "sora":
                if platform == "云雾":
                    model = "sora_image"
                elif platform == "apicore":
                    model = "sora"
                else:
                    model = "sora"
            elif image_model == "nano-banana":
                if platform == "云雾":
                    model = "fal-ai/nano-banana"
                elif platform == "apicore":
                    model = "nano-banana"
                else:
                    model = "nano-banana"
            else:
                model = "sora"  # 默认
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # 使用图像生成测试请求格式
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "生成一个简单的测试图片"
                            }
                        ]
                    }
                ],
                "max_tokens": 100,
                "temperature": 0.7
            }
            
            # 记录测试信息
            logging.info(f"测试API连接: {platform} - {image_model} - {api_url}")
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    QMessageBox.information(self, "测试成功", f"✅ API连接测试成功！\n\n平台: {platform}\n模型: {image_model}\nAPI地址: {api_url}\n状态码: {response.status_code}\n\n响应数据包含: {len(result.get('choices', []))} 个选择项")
                except:
                    QMessageBox.information(self, "测试成功", f"✅ API连接测试成功！\n\n平台: {platform}\n模型: {image_model}\nAPI地址: {api_url}\n状态码: {response.status_code}")
            elif response.status_code == 401:
                QMessageBox.warning(self, "认证失败", f"❌ API密钥认证失败！\n\n请检查API密钥是否正确。\n平台: {platform}\n状态码: {response.status_code}")
            elif response.status_code == 404:
                QMessageBox.warning(self, "模型不存在", f"❌ 模型不存在或不可用！\n\n模型: {model}\n平台: {platform}\n状态码: {response.status_code}\n\n请检查该平台是否支持所选模型。")
            else:
                error_text = response.text[:500] if len(response.text) > 500 else response.text
                QMessageBox.warning(self, "测试失败", f"❌ API连接测试失败！\n\n平台: {platform}\n模型: {image_model}\nAPI地址: {api_url}\n状态码: {response.status_code}\n\n错误信息:\n{error_text}")
                
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "连接超时", f"❌ API连接超时！\n\n请检查网络连接或稍后重试。\n平台: {platform}\nAPI地址: {api_url}")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "连接错误", f"❌ 无法连接到API服务器！\n\n请检查网络连接和API地址。\n平台: {platform}\nAPI地址: {api_url}")
        except Exception as e:
            QMessageBox.critical(self, "测试错误", f"❌ API连接测试失败！\n\n错误类型: {type(e).__name__}\n错误信息: {str(e)}")
        
        finally:
            # 恢复按钮状态
            self.test_api_button.setEnabled(True)
            self.test_api_button.setText("🔗 测试API连接")
    
    def select_save_path(self):
        """选择保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if path:
            self.path_input.setText(path)
    
    def load_settings(self):
        """加载设置到界面"""
        try:
            # 基础配置 - 检查旧的API输入框是否存在
            if hasattr(self, 'api_input'):
                self.api_input.setText(self.api_key)
            
            # 设置分离的API密钥
            if hasattr(self, 'sora_api_input'):
                self.sora_api_input.setText(getattr(self, 'sora_api_key', ''))
            if hasattr(self, 'nano_api_input'):
                self.nano_api_input.setText(getattr(self, 'nano_api_key', ''))
            
            # 其他UI组件 - 安全访问
            if hasattr(self, 'platform_combo'):
                self.platform_combo.setCurrentText(self.api_platform)
            if hasattr(self, 'model_combo'):
                self.model_combo.setCurrentText(self.image_model)
            if hasattr(self, 'thread_spin'):
                self.thread_spin.setValue(self.thread_count)
            if hasattr(self, 'retry_spin'):
                self.retry_spin.setValue(self.retry_count)
            if hasattr(self, 'path_input'):
                self.path_input.setText(self.save_path)
            if hasattr(self, 'ratio_combo'):
                self.ratio_combo.setCurrentText(self.image_ratio)
            
            # 风格库 - 安全访问
            if hasattr(self, 'refresh_style_combo'):
                self.refresh_style_combo()
            if hasattr(self, 'refresh_style_list'):
                self.refresh_style_list()
            if self.current_style and self.current_style in self.style_library and hasattr(self, 'style_combo'):
                self.style_combo.setCurrentText(self.current_style)
                # 确保custom_style_content与选择的风格同步
                if not self.custom_style_content or self.custom_style_content.strip() == "":
                    self.custom_style_content = self.style_library[self.current_style]['content']
            
            # 参考图
            if hasattr(self, 'refresh_category_list'):
                self.refresh_category_list()
            
            # OpenRouter AI优化配置
            if hasattr(self, 'openrouter_key_input'):
                self.openrouter_key_input.setText(self.openrouter_api_key)
            if hasattr(self, 'ai_model_combo'):
                self.ai_model_combo.setCurrentText(self.ai_model)
            if hasattr(self, 'meta_template_combo'):
                self.meta_template_combo.setCurrentText(self.meta_prompt_template)
            if hasattr(self, 'meta_prompt_text'):
                # 如果配置中没有元提示词内容，加载默认模板
                if not self.meta_prompt.strip():
                    if hasattr(self, 'load_meta_template'):
                        self.load_meta_template()
                else:
                    self.meta_prompt_text.setPlainText(self.meta_prompt)
            if hasattr(self, 'update_history_stats'):
                self.update_history_stats()
        
        except Exception as e:
            print(f"加载设置失败: {e}")
            pass
    
    def accept_settings(self):
        """确定：保存设置并关闭"""
        if self.parent():
            # 更新主窗口的配置
            # 保存分离的API密钥
            if hasattr(self, 'sora_api_input'):
                self.parent().sora_api_key = self.sora_api_input.text()
            if hasattr(self, 'nano_api_input'):
                self.parent().nano_api_key = self.nano_api_input.text()
            # 兼容旧的API密钥字段
            if hasattr(self, 'api_input'):
                self.parent().api_key = self.api_input.text()
            
            if hasattr(self, 'platform_combo'):
                self.parent().api_platform = self.platform_combo.currentText()
            if hasattr(self, 'model_combo'):
                self.parent().image_model = self.model_combo.currentText()  # 保存生图模型选择
            
            if hasattr(self, 'thread_spin'):
                self.parent().thread_count = self.thread_spin.value()
            if hasattr(self, 'retry_spin'):
                self.parent().retry_count = self.retry_spin.value()
            if hasattr(self, 'path_input'):
                self.parent().save_path = self.path_input.text()
            if hasattr(self, 'ratio_combo'):
                self.parent().image_ratio = self.ratio_combo.currentText()
            self.parent().style_library = self.style_library
            self.parent().category_links = self.category_links
            self.parent().current_style = self.current_style
            self.parent().custom_style_content = self.custom_style_content
            
            # OpenRouter AI优化配置
            if hasattr(self, 'openrouter_key_input'):
                self.parent().openrouter_api_key = self.openrouter_key_input.text()
                self.parent().ai_model = self.ai_model_combo.currentText()
                self.parent().meta_prompt = self.meta_prompt_text.toPlainText()
                self.parent().meta_prompt_template = self.meta_template_combo.currentText()
                self.parent().optimization_history = self.optimization_history
            
            # 刷新主窗口界面
            self.parent().refresh_ui_after_settings()
            
            # 保存配置
            self.parent().save_config()
        
        # 关闭弹窗
        self.accept()
    
    # ========== 风格库管理方法 ==========
    
    def refresh_style_combo(self):
        """刷新风格选择下拉框"""
        self.style_combo.blockSignals(True)
        self.style_combo.clear()
        self.style_combo.addItem("选择风格...")
        
        for style_name in self.style_library.keys():
            self.style_combo.addItem(style_name)
        
        self.style_combo.blockSignals(False)
        
        # 同步更新主界面的风格选择器（如果主窗口存在且有风格选择器）
        if self.parent() and hasattr(self.parent(), 'main_style_combo'):
            self.parent().refresh_main_style_combo()
    
    def refresh_style_list(self):
        """刷新风格列表"""
        self.style_list.clear()
        for name, style_data in self.style_library.items():
            item = QListWidgetItem(name)
            usage_count = style_data.get('usage_count', 0)
            item.setToolTip(f"使用次数: {usage_count}\n分类: {style_data.get('category', '未分类')}\n创建时间: {style_data.get('created_time', '未知')}")
            self.style_list.addItem(item)
    
    def on_style_changed(self, style_name):
        """风格选择改变时的处理"""
        if style_name == "选择风格..." or style_name == "":
            self.current_style = ""
            self.custom_style_content = ""  # 清空自定义风格内容
        else:
            if style_name in self.style_library:
                self.current_style = style_name
                # 重要：将选中的风格内容同步到custom_style_content
                self.custom_style_content = self.style_library[style_name]['content']
                # 在列表中选中对应项
                items = self.style_list.findItems(style_name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.style_list.setCurrentItem(items[0])
    
    def on_style_list_changed(self, current, previous):
        """风格列表选择改变"""
        if current:
            style_name = current.text()
            if style_name in self.style_library:
                self.load_style_to_editor(style_name)
                self.current_style_name = style_name
                # 更新风格选择状态
                self.current_style = style_name
                self.custom_style_content = self.style_library[style_name]['content']
                # 同步到下拉框
                self.style_combo.blockSignals(True)
                self.style_combo.setCurrentText(style_name)
                self.style_combo.blockSignals(False)
        else:
            self.clear_style_editor()
            self.current_style_name = ""
            self.current_style = ""
            self.custom_style_content = ""
    
    def load_style_to_editor(self, style_name):
        """将风格加载到编辑器"""
        style_data = self.style_library[style_name]
        self.style_name_input.setText(style_name)
        self.style_content_edit.setPlainText(style_data['content'])
        self.update_style_char_count()
    
    def clear_style_editor(self):
        """清空风格编辑器"""
        self.style_name_input.clear()
        self.style_content_edit.clear()
        self.update_style_char_count()
    
    def update_style_char_count(self):
        """更新字符计数"""
        name_len = len(self.style_name_input.text())
        content_len = len(self.style_content_edit.toPlainText())
        self.style_char_count.setText(f"名称: {name_len} 字符 | 内容: {content_len} 字符")
    
    def on_style_content_changed(self):
        """风格内容改变时的处理"""
        # 实时更新custom_style_content，确保与编辑器内容同步
        self.custom_style_content = self.style_content_edit.toPlainText()
    
    def new_style(self):
        """新建风格"""
        new_name = self.generate_new_style_name()
        
        new_style = {
            'name': new_name,
            'content': '',
            'category': '自定义风格',
            'created_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'usage_count': 0
        }
        
        self.style_library[new_name] = new_style
        self.refresh_style_list()
        self.refresh_style_combo()
        
        items = self.style_list.findItems(new_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.style_list.setCurrentItem(items[0])
    
    def generate_new_style_name(self):
        """生成新的风格名称"""
        base_name = "新风格"
        counter = 1
        new_name = base_name
        
        while new_name in self.style_library:
            new_name = f"{base_name}{counter}"
            counter += 1
        
        return new_name
    
    def copy_style(self):
        """复制当前选中的风格"""
        if not self.current_style_name:
            QMessageBox.warning(self, "提示", "请先选择要复制的风格")
            return
        
        original_style = self.style_library[self.current_style_name]
        copy_name = f"{self.current_style_name}_副本"
        counter = 1
        
        while copy_name in self.style_library:
            copy_name = f"{self.current_style_name}_副本{counter}"
            counter += 1
        
        copied_style = {
            'name': copy_name,
            'content': original_style['content'],
            'category': original_style['category'],
            'created_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'usage_count': 0
        }
        
        self.style_library[copy_name] = copied_style
        self.refresh_style_list()
        self.refresh_style_combo()
        
        items = self.style_list.findItems(copy_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.style_list.setCurrentItem(items[0])
    
    def delete_style(self):
        """删除当前选中的风格"""
        if not self.current_style_name:
            QMessageBox.warning(self, "提示", "请先选择要删除的风格")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除风格 '{self.current_style_name}' 吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.style_library[self.current_style_name]
            self.refresh_style_list()
            self.refresh_style_combo()
            self.clear_style_editor()
            self.current_style_name = ""
    
    def save_current_style(self):
        """保存当前编辑的风格"""
        new_name = self.style_name_input.text().strip()
        new_content = self.style_content_edit.toPlainText().strip()
        
        if not new_name:
            QMessageBox.warning(self, "错误", "风格名称不能为空！")
            return
        
        if not new_content:
            QMessageBox.warning(self, "错误", "风格内容不能为空！")
            return
        
        if new_name != self.current_style_name and new_name in self.style_library:
            QMessageBox.warning(self, "错误", f"风格名称 '{new_name}' 已存在！")
            return
        
        if self.current_style_name and new_name != self.current_style_name:
            old_data = self.style_library[self.current_style_name]
            del self.style_library[self.current_style_name]
            
            self.style_library[new_name] = {
                'name': new_name,
                'content': new_content,
                'category': old_data.get('category', '自定义风格'),
                'created_time': old_data.get('created_time', time.strftime('%Y-%m-%d %H:%M:%S')),
                'usage_count': old_data.get('usage_count', 0)
            }
        else:
            if self.current_style_name in self.style_library:
                self.style_library[self.current_style_name]['content'] = new_content
                if new_name != self.current_style_name:
                    self.style_library[self.current_style_name]['name'] = new_name
            else:
                self.style_library[new_name] = {
                    'name': new_name,
                    'content': new_content,
                    'category': '自定义风格',
                    'created_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'usage_count': 0
                }
        
        self.current_style_name = new_name
        self.refresh_style_list()
        self.refresh_style_combo()
        
        items = self.style_list.findItems(new_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.style_list.setCurrentItem(items[0])
        
        QMessageBox.information(self, "成功", f"风格 '{new_name}' 已保存！")
    
    def import_styles(self):
        """从文件导入风格"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "导入风格文件", 
            "", 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                
                imported_count = 0
                for name, style_data in imported_data.items():
                    final_name = name
                    counter = 1
                    while final_name in self.style_library:
                        final_name = f"{name}_导入{counter}"
                        counter += 1
                    
                    self.style_library[final_name] = style_data
                    imported_count += 1
                
                self.refresh_style_list()
                self.refresh_style_combo()
                QMessageBox.information(self, "导入成功", f"成功导入 {imported_count} 个风格")
                
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入风格失败: {str(e)}")
    
    def export_styles(self):
        """导出风格到文件"""
        if not self.style_library:
            QMessageBox.warning(self, "提示", "没有可导出的风格")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出风格文件",
            f"sora_styles_{time.strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.style_library, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "导出成功", f"已导出 {len(self.style_library)} 个风格到:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出风格失败: {str(e)}")
    
    def reset_default_styles(self):
        """重置为默认风格"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置为默认风格库吗？\n这将清除所有自定义风格！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.style_library = {
                '超写实风格': {
                    'name': '超写实风格',
                    'content': '极致的超写实主义照片风格，画面呈现出顶级数码单反相机（如佳能EOS R5）搭配高质量定焦镜头（如85mm f/1.2）的拍摄效果。明亮、均匀，光影过渡微妙且真实，无明显阴影。绝对真实的全彩照片，无任何色彩滤镜。色彩如同在D65标准光源环境下拍摄，白平衡极其精准，所见即所得。色彩干净通透，类似于现代商业广告摄影风格。严禁任何形式的棕褐色调、复古滤镜或暖黄色偏色。画面高度细腻，细节极其丰富，达到8K分辨率的视觉效果。追求极致的清晰度和纹理表现，所有物体的材质质感都应逼真呈现，无噪点，无失真。',
                    'category': '摄影风格',
                    'created_time': '2024-01-01 12:00:00',
                    'usage_count': 0
                },
                '动漫风格': {
                    'name': '动漫风格',
                    'content': '二次元动漫风格，色彩鲜艳饱满，线条清晰，具有典型的日式动漫美学特征。人物造型精致，表情生动，背景细腻。',
                    'category': '插画风格',
                    'created_time': '2024-01-01 12:01:00',
                    'usage_count': 0
                },
                '油画风格': {
                    'name': '油画风格',
                    'content': '经典油画艺术风格，笔触丰富，色彩层次分明，具有厚重的质感和艺术气息。光影效果自然，构图典雅。',
                    'category': '艺术风格',
                    'created_time': '2024-01-01 12:02:00',
                    'usage_count': 0
                }
            }
            
            self.refresh_style_list()
            self.refresh_style_combo()
            self.clear_style_editor()
            self.current_style_name = ""
            
            QMessageBox.information(self, "重置完成", "已重置为默认风格库")
    
    # ========== 参考图管理方法 ==========
    
    def refresh_category_list(self):
        """刷新分类列表"""
        self.category_list.clear()
        for category in self.category_links.keys():
            item = QListWidgetItem(category)
            image_count = len(self.category_links[category])
            item.setToolTip(f"图片数量: {image_count}")
            self.category_list.addItem(item)
    
    def on_category_changed(self, current, previous):
        """分类选择改变"""
        if current:
            category_name = current.text()
            self.current_category = category_name
            self.load_images_to_table(category_name)
        else:
            self.clear_image_table()
            self.current_category = ""
    
    def load_images_to_table(self, category_name):
        """将图片加载到表格"""
        images = self.category_links.get(category_name, [])
        self.image_table.setRowCount(len(images))
        
        self.image_table.blockSignals(True)
        for row, image in enumerate(images):
            name_item = QTableWidgetItem(image.get('name', ''))
            self.image_table.setItem(row, 0, name_item)
            
            # 显示路径或URL
            if 'path' in image and image['path']:
                # 本地图片，显示路径
                path_item = QTableWidgetItem(image['path'])
                path_item.setToolTip(f"本地图片: {image['path']}")
            else:
                # 网络图片，显示URL
                path_item = QTableWidgetItem(image.get('url', ''))
                path_item.setToolTip(f"网络图片: {image.get('url', '')}")
            
            self.image_table.setItem(row, 1, path_item)
        self.image_table.blockSignals(False)
    
    def clear_image_table(self):
        """清空图片表格"""
        self.image_table.setRowCount(0)
    
    def new_category(self):
        """新建分类"""
        name, ok = QInputDialog.getText(self, "新建分类", "请输入分类名称:")
        if ok and name and name not in self.category_links:
            # 创建分类配置
            self.category_links[name] = []
            # 创建分类目录
            create_category_directory(name)
            self.refresh_category_list()
            items = self.category_list.findItems(name, Qt.MatchFlag.MatchExactly)
            if items:
                self.category_list.setCurrentItem(items[0])
            logging.info(f"创建新分类: {name}")
        elif ok and name in self.category_links:
            QMessageBox.warning(self, "错误", "分类名称已存在！")
    
    def rename_category(self):
        """重命名当前分类"""
        if not self.current_category:
            QMessageBox.warning(self, "提示", "请先选择要重命名的分类")
            return
            
        name, ok = QInputDialog.getText(self, "重命名分类", "请输入新名称:", text=self.current_category)
        if ok and name and name != self.current_category:
            if name in self.category_links:
                QMessageBox.warning(self, "错误", "分类名称已存在！")
                return
            
            # 更新配置
            old_category = self.current_category
            self.category_links[name] = self.category_links.pop(self.current_category)
            
            # 重命名目录
            rename_category_directory(old_category, name)
            
            # 更新图片路径（如果有本地图片的话）
            for image in self.category_links[name]:
                if 'path' in image and image['path'].startswith(f"images/{old_category}/"):
                    image['path'] = image['path'].replace(f"images/{old_category}/", f"images/{name}/")
            
            self.current_category = name
            self.refresh_category_list()
            
            items = self.category_list.findItems(name, Qt.MatchFlag.MatchExactly)
            if items:
                self.category_list.setCurrentItem(items[0])
            
            logging.info(f"重命名分类: {old_category} -> {name}")
    
    def delete_category(self):
        """删除当前选中的分类"""
        if not self.current_category:
            QMessageBox.warning(self, "提示", "请先选择要删除的分类")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除分类 '{self.current_category}' 吗？\n此操作会删除分类目录下的所有图片文件，不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 删除目录及其内容
            delete_category_directory(self.current_category)
            # 删除配置
            del self.category_links[self.current_category]
            self.refresh_category_list()
            self.clear_image_table()
            logging.info(f"删除分类: {self.current_category}")
            self.current_category = ""
    
    def add_image(self):
        """添加图片"""
        try:
            if not self.current_category:
                QMessageBox.warning(self, "提示", "请先选择分类")
                return
            
            # 弹出文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择图片文件",
                "",
                "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;所有文件 (*)"
            )
            
            if file_path:
                # 检查文件是否存在
                if not Path(file_path).exists():
                    QMessageBox.critical(self, "错误", f"选择的文件不存在: {file_path}")
                    return
                
                # 获取图片名称（用户可以修改）
                default_name = Path(file_path).stem
                name, ok = QInputDialog.getText(
                    self, 
                    "输入图片名称", 
                    "请输入图片名称（用于在提示词中引用）:",
                    text=default_name
                )
                
                if ok and name:
                    if not name.strip():
                        QMessageBox.warning(self, "错误", "图片名称不能为空")
                        return
                        
                    try:
                        # 检查category_links是否已初始化
                        if not hasattr(self, 'category_links') or not self.category_links:
                            QMessageBox.critical(self, "错误", "图库分类未初始化，请重新打开设置")
                            return
                            
                        if self.current_category not in self.category_links:
                            self.category_links[self.current_category] = []
                        
                        # 复制图片到分类目录
                        relative_path = copy_image_to_category(file_path, self.current_category, name.strip())
                        
                        # 添加到配置中
                        images = self.category_links[self.current_category]
                        images.append({
                            'name': name.strip(),
                            'path': relative_path,
                            'url': ''  # 保留URL字段以兼容旧版本
                        })
                        
                        self.load_images_to_table(self.current_category)
                        QMessageBox.information(self, "成功", f"图片 '{name}' 已添加到分类 '{self.current_category}'")
                        
                    except PermissionError as e:
                        QMessageBox.critical(self, "权限错误", f"没有权限访问文件或创建目录:\n{str(e)}\n\n请以管理员身份运行程序")
                        logging.error(f"权限错误: {e}")
                    except FileNotFoundError as e:
                        QMessageBox.critical(self, "文件错误", f"文件或目录不存在:\n{str(e)}")
                        logging.error(f"文件不存在错误: {e}")
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"添加图片失败:\n{str(e)}")
                        logging.error(f"添加图片失败: {e}", exc_info=True)
                        
        except Exception as e:
            QMessageBox.critical(self, "严重错误", f"图片添加过程中发生未预期的错误:\n{str(e)}")
            logging.error(f"图片添加严重错误: {e}", exc_info=True)
    
    def delete_image(self):
        """删除选中的图片"""
        if not self.current_category:
            QMessageBox.warning(self, "提示", "请先选择分类")
            return
        
        selected_rows = set(idx.row() for idx in self.image_table.selectedIndexes())
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的图片")
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 张图片吗？\n此操作会删除本地图片文件，不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            images = self.category_links[self.current_category]
            deleted_count = 0
            
            for row in sorted(selected_rows, reverse=True):
                if 0 <= row < len(images):
                    image = images[row]
                    
                    # 删除本地文件（如果存在path字段）
                    if 'path' in image and image['path']:
                        local_path = APP_PATH / image['path']
                        if local_path.exists():
                            try:
                                local_path.unlink()
                                logging.info(f"删除本地图片文件: {local_path}")
                            except Exception as e:
                                logging.error(f"删除本地图片文件失败: {e}")
                    
                    # 从配置中删除
                    images.pop(row)
                    deleted_count += 1
            
            self.load_images_to_table(self.current_category)
            if deleted_count > 0:
                QMessageBox.information(self, "删除完成", f"已删除 {deleted_count} 张图片")
    
    def on_image_changed(self, row, column):
        """图片信息改变时"""
        if not self.current_category:
            return
        
        images = self.category_links[self.current_category]
        if 0 <= row < len(images):
            name = self.image_table.item(row, 0).text() if self.image_table.item(row, 0) else ''
            path_or_url = self.image_table.item(row, 1).text() if self.image_table.item(row, 1) else ''
            
            # 如果是路径格式（以images/开头），更新path字段；否则更新url字段
            if path_or_url.startswith('images/'):
                images[row] = {'name': name, 'path': path_or_url, 'url': images[row].get('url', '')}
            else:
                images[row] = {'name': name, 'url': path_or_url, 'path': images[row].get('path', '')}
    
    def on_image_table_double_clicked(self, row, column):
        """图片表格双击事件 - 预览图片"""
        if not self.current_category:
            return
        
        images = self.category_links[self.current_category]
        if 0 <= row < len(images):
            image = images[row]
            image_name = image.get('name', '')
            
            if 'path' in image and image['path']:
                # 本地图片预览
                local_path = APP_PATH / image['path']
                if local_path.exists():
                    self.show_image_preview(image_name, str(local_path), is_local=True)
                else:
                    QMessageBox.warning(self, "文件不存在", f"本地图片文件不存在:\n{local_path}")
            elif 'url' in image and image['url']:
                # 网络图片预览（显示URL信息）
                self.show_image_preview(image_name, image['url'], is_local=False)
            else:
                QMessageBox.information(self, "提示", "该图片没有有效的路径或链接")
    
    def show_image_preview(self, image_name, path_or_url, is_local=True):
        """显示图片预览对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"图片预览 - {image_name}")
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # 图片显示区域
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("border: 1px solid #ddd; background-color: #f9f9f9;")
        image_label.setMinimumSize(500, 400)
        
        if is_local:
            # 本地图片
            try:
                pixmap = QPixmap(path_or_url)
                if not pixmap.isNull():
                    # 缩放图片以适应显示区域
                    scaled_pixmap = pixmap.scaled(
                        480, 380,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setText("无法加载图片")
            except Exception as e:
                image_label.setText(f"加载图片失败:\n{str(e)}")
        else:
            # 网络图片显示链接信息
            image_label.setText(f"网络图片:\n{path_or_url}\n\n(双击此区域在浏览器中打开)")
            image_label.setWordWrap(True)
            image_label.mousePressEvent = lambda event: self.open_url_in_browser(path_or_url)
            image_label.setStyleSheet("border: 1px solid #ddd; background-color: #f0f8ff; padding: 20px; cursor: pointer;")
        
        layout.addWidget(image_label)
        
        # 信息标签
        info_label = QLabel(f"图片名称: {image_name}\n路径: {path_or_url}")
        info_label.setStyleSheet("color: #666; font-size: 14px; padding: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.exec()
    
    def open_url_in_browser(self, url):
        """在浏览器中打开URL"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开链接: {str(e)}")

class PromptEditDialog(QDialog):
    """提示词编辑对话框"""
    
    def __init__(self, prompt_text, prompt_number, parent=None):
        super().__init__(parent)
        self.prompt_text = prompt_text
        self.prompt_number = prompt_number
        self.setWindowTitle(f"编辑提示词 - 编号: {prompt_number}")
        self.setModal(True)
        self.resize(700, 500)
        self.setMinimumSize(600, 400)
        
        # 设置窗口居中
        self.center_on_screen()
        
        self.setup_ui()
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QTextEdit {
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                background-color: white;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #1976d2;
            }
            QPushButton {
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton#confirm {
                background-color: #4caf50;
                color: white;
                border: none;
            }
            QPushButton#confirm:hover {
                background-color: #45a049;
            }
            QPushButton#cancel {
                background-color: #f44336;
                color: white;
                border: none;
            }
            QPushButton#cancel:hover {
                background-color: #da190b;
            }
        """)
    
    def center_on_screen(self):
        """将对话框居中显示"""
        if self.parent():
            parent_geometry = self.parent().geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)
    
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题和说明
        title_label = QLabel(f"📝 编辑提示词 (编号: {self.prompt_number})")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 提示信息
        hint_label = QLabel("💡 在下方文本框中编辑您的提示词，支持多行文本和换行。")
        hint_label.setStyleSheet("color: #666; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(hint_label)
        
        # 文本编辑区域
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText(self.prompt_text)
        self.text_edit.setPlaceholderText("请输入您的提示词内容...")
        
        # 设置字体
        font = QFont()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(14)
        self.text_edit.setFont(font)
        
        layout.addWidget(self.text_edit)
        
        # 字符计数标签
        self.char_count_label = QLabel()
        self.char_count_label.setStyleSheet("color: #666; font-size: 14px;")
        self.update_char_count()
        layout.addWidget(self.char_count_label)
        
        # 连接文本变化事件
        self.text_edit.textChanged.connect(self.update_char_count)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 取消按钮
        cancel_button = QPushButton("❌ 取消")
        cancel_button.setObjectName("cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # 确认按钮
        confirm_button = QPushButton("✅ 确认保存")
        confirm_button.setObjectName("confirm")
        confirm_button.clicked.connect(self.accept)
        confirm_button.setDefault(True)  # 设置为默认按钮
        button_layout.addWidget(confirm_button)
        
        layout.addLayout(button_layout)
        
        # 设置焦点到文本编辑框
        self.text_edit.setFocus()
        
        # 选中所有文本，方便编辑
        self.text_edit.selectAll()
        
        # 添加快捷键支持
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Ctrl+S 保存
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.accept)
        
        # Esc 取消
        cancel_shortcut = QShortcut(QKeySequence("Esc"), self)
        cancel_shortcut.activated.connect(self.reject)
    
    def update_char_count(self):
        """更新字符计数"""
        text = self.text_edit.toPlainText()
        char_count = len(text)
        line_count = len(text.split('\n'))
        self.char_count_label.setText(f"字符数: {char_count} | 行数: {line_count}")
    
    def get_text(self):
        """获取编辑后的文本"""
        return self.text_edit.toPlainText().strip()

class ImageViewDialog(QDialog):
    """图片查看对话框"""
    
    def __init__(self, image_number, prompt_text, save_path, parent=None):
        super().__init__(parent)
        self.image_number = image_number
        self.prompt_text = prompt_text
        self.save_path = save_path
        self.setWindowTitle(f"图片预览 - {prompt_text[:30]}...")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # 图片显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #ddd; background-color: #f9f9f9;")
        self.image_label.setText("正在加载图片...")
        
        layout.addWidget(self.image_label)
        
        # 底部信息和按钮
        info_layout = QHBoxLayout()
        
        info_label = QLabel(f"提示词: {prompt_text}")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 14px;")
        info_layout.addWidget(info_label)
        
        info_layout.addStretch()
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        info_layout.addWidget(close_button)
        
        layout.addLayout(info_layout)
        
        # 加载图片
        self.load_image()
    
    def load_image(self):
        """从本地文件加载并显示图片"""
        try:
            # 检查保存路径
            if not self.save_path:
                self.image_label.setText("保存路径未设置")
                return
            
            # 从数据中获取实际的文件名
            filename = None
            if hasattr(self.parent(), 'prompt_table_data'):
                for data in self.parent().prompt_table_data:
                    if data['number'] == self.image_number:
                        filename = data.get('filename')
                        break
            
            # 如果没有找到文件名，使用旧的命名规则作为后备
            if not filename:
                filename = f"{self.image_number}.png"
            
            file_path = os.path.join(self.save_path, filename)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                self.image_label.setText(f"本地图片文件不存在:\n{filename}")
                return
            
            # 从本地文件加载图片
            pixmap = QPixmap(file_path)
            
            if not pixmap.isNull():
                # 缩放图片以适应窗口，保持比例
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size() - QSize(20, 20),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("图片文件格式错误")
                
        except Exception as e:
            self.image_label.setText(f"本地图片加载失败:\n{str(e)}")

class TextReplaceDialog(QDialog):
    """文字替换对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔄 文字替换工具")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 说明文字
        info_label = QLabel("在所有提示词输入框中查找并替换文字")
        info_label.setStyleSheet("color: #666; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 查找文字输入框
        find_group = QGroupBox("🔍 查找文字")
        find_layout = QVBoxLayout(find_group)
        
        self.find_text = QLineEdit()
        self.find_text.setPlaceholderText("请输入要查找的文字...")
        self.find_text.setStyleSheet("padding: 8px; font-size: 14px;")
        find_layout.addWidget(self.find_text)
        
        layout.addWidget(find_group)
        
        # 替换文字输入框
        replace_group = QGroupBox("✏️ 替换为")
        replace_layout = QVBoxLayout(replace_group)
        
        # 替换文字输入区域
        replace_input_layout = QHBoxLayout()
        
        self.replace_text = QLineEdit()
        self.replace_text.setPlaceholderText("请输入替换后的文字...")
        self.replace_text.setStyleSheet("padding: 8px; font-size: 14px;")
        replace_input_layout.addWidget(self.replace_text)
        
        # 从图库选择按钮
        self.gallery_button = QPushButton("图库")
        self.gallery_button.setToolTip("从图库中选择图片名称")
        self.gallery_button.clicked.connect(self.select_from_gallery)
        self.gallery_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:pressed {
                background-color: #cc7a00;
            }
        """)
        replace_input_layout.addWidget(self.gallery_button)
        
        replace_layout.addLayout(replace_input_layout)
        
        layout.addWidget(replace_group)
        
        # 预览区域
        preview_group = QGroupBox("👁️ 预览结果")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QPlainTextEdit()
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("预览将要被替换的内容...")
        self.preview_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd;")
        preview_layout.addWidget(self.preview_text)
        
        layout.addWidget(preview_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("预览")
        self.preview_button.clicked.connect(self.preview_replacement)
        self.preview_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        button_layout.addWidget(self.preview_button)
        
        self.replace_button = QPushButton("执行替换")
        self.replace_button.clicked.connect(self.accept)
        self.replace_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        button_layout.addWidget(self.replace_button)
        
        cancel_button = QPushButton("❌ 取消")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # 设置父窗口引用用于预览
        self.parent_window = parent
    
    def preview_replacement(self):
        """预览替换结果"""
        find_text = self.find_text.text().strip()
        replace_text = self.replace_text.text()
        
        if not find_text:
            QMessageBox.warning(self, "提示", "请输入要查找的文字")
            return
        
        if not hasattr(self.parent_window, 'prompt_table_data'):
            self.preview_text.setPlainText("无提示词数据")
            return
        
        preview_lines = []
        match_count = 0
        
        for i, data in enumerate(self.parent_window.prompt_table_data):
            prompt = data['prompt']
            if find_text in prompt:
                match_count += 1
                # 显示前后对比
                new_prompt = prompt.replace(find_text, replace_text)
                preview_lines.append(f"#{data['number']}:")
                preview_lines.append(f"原文: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
                preview_lines.append(f"替换后: {new_prompt[:50]}{'...' if len(new_prompt) > 50 else ''}")
                preview_lines.append("-" * 40)
        
        if match_count == 0:
            preview_lines.append("未找到匹配的文字")
        else:
            preview_lines.insert(0, f"找到 {match_count} 个匹配项:")
            preview_lines.insert(1, "=" * 40)
        
        self.preview_text.setPlainText("\n".join(preview_lines))
    
    def select_from_gallery(self):
        """从图库中选择图片名称"""
        if not hasattr(self.parent_window, 'category_links') or not self.parent_window.category_links:
            QMessageBox.warning(self, "提示", "图库为空，请先在设置中心配置参考图库")
            return
        
        try:
            dialog = GallerySelectionDialog(self.parent_window.category_links, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_image = dialog.get_selected_image()
                if selected_image:
                    # 将选中的图片名称设置到替换文本框中，用「」包围
                    image_name = f"「{selected_image}」"
                    self.replace_text.setText(image_name)
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开图库时发生错误: {str(e)}")
    
    def get_replacement_data(self):
        """获取替换数据"""
        return {
            'find_text': self.find_text.text().strip(),
            'replace_text': self.replace_text.text()
        }

class GallerySelectionDialog(QDialog):
    """图库选择对话框"""
    
    def __init__(self, category_links, parent=None):
        super().__init__(parent)
        self.category_links = category_links
        self.selected_image = None
        
        self.setWindowTitle("🖼️ 图库选择")
        self.setModal(True)
        self.resize(700, 600)  # 增加宽度和高度以更好地显示缩略图
        
        layout = QVBoxLayout(self)
        
        # 说明文字
        info_label = QLabel("从参考图库中选择图片，选择后图片名称将添加到提示词中")
        info_label.setStyleSheet("color: #666; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 分类选择
        category_group = QGroupBox("📁 选择图片分类")
        category_layout = QVBoxLayout(category_group)
        
        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet("padding: 8px; font-size: 14px;")
        self.category_combo.addItem("请选择分类...")
        
        for category_name in self.category_links.keys():
            self.category_combo.addItem(category_name)
        
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        category_layout.addWidget(self.category_combo)
        
        layout.addWidget(category_group)
        
        # 图片列表
        images_group = QGroupBox("🖼️ 选择图片")
        images_layout = QVBoxLayout(images_group)
        
        self.images_list = QListWidget()
        self.images_list.setViewMode(QListWidget.ViewMode.IconMode)  # 图标模式
        self.images_list.setIconSize(QSize(120, 120))  # 设置图标大小
        self.images_list.setGridSize(QSize(140, 140))  # 设置网格大小
        self.images_list.setResizeMode(QListWidget.ResizeMode.Adjust)  # 自动调整
        self.images_list.setMovement(QListWidget.Movement.Static)  # 静态模式
        self.images_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
                border: 1px solid #eee;
                border-radius: 4px;
                margin: 2px;
                text-align: center;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border-color: #1976d2;
                color: #1976d2;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
                border-color: #bbb;
            }
        """)
        self.images_list.itemDoubleClicked.connect(self.on_image_double_clicked)
        images_layout.addWidget(self.images_list)
        
        layout.addWidget(images_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("✅ 选择此图片")
        self.select_button.clicked.connect(self.accept)
        self.select_button.setEnabled(False)
        self.select_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        button_layout.addWidget(self.select_button)
        
        cancel_button = QPushButton("❌ 取消")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # 连接列表选择事件
        self.images_list.currentItemChanged.connect(self.on_image_selection_changed)
    
    def on_category_changed(self, category_name):
        """分类选择改变"""
        self.images_list.clear()
        self.selected_image = None
        self.select_button.setEnabled(False)
        
        if category_name == "请选择分类..." or category_name not in self.category_links:
            return
        
        # 加载该分类的图片，包含缩略图
        for image_info in self.category_links[category_name]:
            item = QListWidgetItem()
            item.setText(image_info['name'])
            item.setData(Qt.ItemDataRole.UserRole, image_info)
            
            # 构建图片完整路径
            if hasattr(self.parent(), 'save_path') and self.parent().save_path:
                # 如果图片路径不是绝对路径，则相对于项目目录
                if not os.path.isabs(image_info['path']):
                    image_full_path = os.path.join(str(APP_PATH), image_info['path'])
                else:
                    image_full_path = image_info['path']
            else:
                # 相对于项目目录
                image_full_path = os.path.join(str(APP_PATH), image_info['path'])
            
            # 获取缩略图
            thumbnail = get_cached_thumbnail(image_full_path)
            if thumbnail and not thumbnail.isNull():
                item.setIcon(QIcon(thumbnail))
            else:
                # 如果无法加载缩略图，使用默认图标
                item.setIcon(QIcon())
                
            item.setToolTip(f"{image_info['name']}\n路径: {image_info['path']}")
            self.images_list.addItem(item)
    
    def on_image_selection_changed(self, current_item, previous_item):
        """图片选择改变"""
        if current_item:
            self.selected_image = current_item.data(Qt.ItemDataRole.UserRole)
            self.select_button.setEnabled(True)
        else:
            self.selected_image = None
            self.select_button.setEnabled(False)
    
    def on_image_double_clicked(self, item):
        """图片双击选择"""
        if item:
            self.selected_image = item.data(Qt.ItemDataRole.UserRole)
            self.accept()
    
    def get_selected_image(self):
        """获取选择的图片名称"""
        if self.selected_image and isinstance(self.selected_image, dict):
            return self.selected_image.get('name', '')
        return self.selected_image

class PromptTableDelegate(QStyledItemDelegate):
    """自定义表格委托，处理编辑和显示"""
    
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
    
    def createEditor(self, parent, option, index):
        """创建编辑器"""
        if index.column() == 1:  # 编号列，允许直接编辑
            editor = QLineEdit(parent)
            editor.setStyleSheet("""
                QLineEdit {
                    border: 2px solid #1976d2;
                    border-radius: 4px;
                    padding: 4px;
                    background-color: white;
                }
            """)
            return editor
        elif index.column() == 2:  # 提示词列现在使用内嵌编辑器，不需要委托处理
            return None
        return super().createEditor(parent, option, index)
    
    def setEditorData(self, editor, index):
        """设置编辑器数据"""
        value = index.model().data(index, Qt.ItemDataRole.EditRole)
        if isinstance(editor, QLineEdit):
            editor.setText(str(value))
            editor.selectAll()
        elif isinstance(editor, QPlainTextEdit):
            editor.setPlainText(str(value))
            editor.selectAll()
        else:
            super().setEditorData(editor, index)
    
    def setModelData(self, editor, model, index):
        """将编辑器数据设置回模型"""
        if isinstance(editor, QLineEdit):
            # 移除首尾空白字符
            text = editor.text().strip()
            model.setData(index, text, Qt.ItemDataRole.EditRole)
            # 记录光标位置，但不立即清理活跃编辑器（图库对话框可能需要它）
            if self.main_window and index.column() == 1:
                cursor_pos = editor.cursorPosition()
                self.main_window.record_cursor_position(index.row(), cursor_pos)
        elif isinstance(editor, QPlainTextEdit):
            # 获取多行文本，保留换行符但移除首尾空白
            text = editor.toPlainText().strip()
            model.setData(index, text, Qt.ItemDataRole.EditRole)
            # 记录光标位置，但不立即清理活跃编辑器（图库对话框可能需要它）
            if self.main_window and index.column() == 2:
                cursor_pos = editor.textCursor().position()
                self.main_window.record_cursor_position(index.row(), cursor_pos)
        else:
            super().setModelData(editor, model, index)
    
    def paint(self, painter, option, index):
        """自定义绘制，支持换行显示"""
        if index.column() == 1:  # 提示词列
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if text:
                # 设置绘制区域
                rect = option.rect
                rect.adjust(8, 5, -8, -5)  # 添加一些边距
                
                # 设置字体和颜色
                painter.setFont(option.font)
                painter.setPen(option.palette.color(QPalette.ColorRole.Text))
                
                # 如果选中，设置选中样式
                if option.state & QStyle.StateFlag.State_Selected:
                    painter.fillRect(option.rect, option.palette.color(QPalette.ColorRole.Highlight))
                    painter.setPen(option.palette.color(QPalette.ColorRole.HighlightedText))
                
                # 绘制文本，支持换行和换行符
                painter.drawText(rect, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, text)
                return
        
        # 其他列使用默认绘制
        super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        """计算单元格大小提示"""
        if index.column() == 1:  # 提示词列
            text = index.data(Qt.ItemDataRole.DisplayRole)
            if text:
                # 计算文本需要的高度
                font_metrics = option.fontMetrics
                # 获取列宽
                column_width = 300  # 默认宽度，实际会由表格调整
                if hasattr(option, 'rect'):
                    column_width = option.rect.width() - 10  # 减去边距
                
                # 计算换行后的高度
                text_rect = font_metrics.boundingRect(0, 0, column_width, 0, Qt.TextFlag.TextWordWrap, text)
                height = max(200, text_rect.height() + 20)  # 最小200像素，与图片行高保持一致
                return QSize(column_width, height)
        
        return super().sizeHint(option, index)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_done = False
        self.setWindowTitle("深海圈生图 - AI批量生图工具")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 600)
        
        # 配置变量
        self.api_key = ""
        self.api_platform = "云雾"
        self.image_model = "sora"  # 添加生图模型配置
        # 分离的API密钥初始化
        self.sora_api_key = ""
        self.nano_api_key = ""
        self.thread_count = 5
        self.retry_count = 3
        self.save_path = ""
        self.image_ratio = "3:2"
        self.style_library = {}
        self.category_links = {}
        self.current_style = ""
        self.custom_style_content = ""
        
        # OpenRouter AI优化配置
        self.openrouter_api_key = ""
        self.ai_model = "qwen/qwq-32b"
        self.meta_prompt = ""
        self.meta_prompt_template = "template1"
        self.optimization_history = []
        
        # 添加计数器变量
        self.total_images = 0
        self.completed_images = 0
        
        # 提示词数据存储
        self.prompt_table_data = []  # [{number, prompt, status, image_url, error_msg}]
        
        # 异步设置样式（避免阻塞启动）
        QTimer.singleShot(0, self.setup_modern_style)
        
        # 创建主窗口
        self.setup_ui()
        
        # 初始化线程池
        self.threadpool = QThreadPool()
        
        # 存储提示词和编号的对应关系
        self.prompt_numbers = {}
        
        # 存储每行的光标位置 {row: cursor_position}
        self.cursor_positions = {}
        self.active_editors = {}  # 记录当前活跃的编辑器
        self.focused_row = -1  # 当前焦点行，用于图片插入时的光标定位
        
        # 异步初始化：延迟非关键操作
        QTimer.singleShot(0, self.delayed_initialization)
        
        # 存储生成的图片信息
        self.generated_images = {}
        
        self._init_done = True
    
    def get_current_api_key(self):
        """根据选择的模型获取对应的API密钥"""
        if self.image_model == "sora":
            return getattr(self, 'sora_api_key', '')
        elif self.image_model == "fal-ai/nano-banana":
            return getattr(self, 'nano_api_key', '')
        else:
            # 默认返回旧的API密钥以保持兼容性
            return getattr(self, 'api_key', '')
    
    def on_model_changed(self, model_name):
        """模型选择改变时更新主界面显示"""
        try:
            # 只更新右上角API状态显示，移除左上角生图模型显示
            if hasattr(self, 'api_status_label'):
                api_key = self.get_current_api_key()
                if api_key and api_key.strip():
                    # 根据模型显示不同的emoji和颜色
                    if model_name == "sora":
                        model_emoji = "🌊"
                        model_color = "#17a2b8"
                    elif model_name == "nano-banana":
                        model_emoji = "🍌" 
                        model_color = "#fd7e14"
                    else:
                        model_emoji = "🤖"
                        model_color = "#28a745"
                    
                    self.api_status_label.setText(f"{model_emoji} {model_name} 模型 | {self.api_platform} 平台")
                    self.api_status_label.setStyleSheet(f"""
                        QLabel {{
                            color: #ffffff; 
                            font-size: 14px; 
                            font-weight: bold;
                            padding: 8px 14px;
                            background-color: {model_color};
                            border: 2px solid rgba(255, 255, 255, 0.3);
                            border-radius: 8px;
                            margin-right: 10px;
                        }}
                    """)
                
        except Exception as e:
            print(f"模型显示更新失败: {e}")
    
    def delayed_initialization(self):
        """延迟初始化非关键组件"""
        # 检查并自动生成默认配置文件
        self.check_default_config()
        
        # 加载配置
        self.load_config()
        
        # 后台创建目录（避免阻塞UI）
        QTimer.singleShot(100, self.create_directories_async)
    
    def create_directories_async(self):
        """异步创建目录"""
        # 确保图片目录存在
        ensure_images_directory()
        
        # 确保缩略图缓存目录存在
        ensure_thumbnail_cache_directory()
        
        # 为现有分类创建目录（兼容旧版本）
        for category_name in self.category_links.keys():
            create_category_directory(category_name)
        
        # 确保主界面风格选择器显示正确的当前风格
        if hasattr(self, 'main_style_combo'):
            self.refresh_main_style_combo()
        
    def setup_modern_style(self):
        """设置现代化样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333;
            }
            
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 10px 18px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 16px;
            }
            
            QPushButton:hover {
                background-color: #1565c0;
            }
            
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            
            QPushButton:disabled {
                background-color: #ccc;
            }
            
            QLineEdit, QComboBox, QSpinBox {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 16px;
            }
            
            QLineEdit:focus, QComboBox:focus {
                border-color: #1976d2;
            }
            
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
                font-size: 16px;
            }
            
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                gridline-color: #eee;
                selection-background-color: #e9ecef;
                selection-color: black;
            }
            
            QTableWidget::item {
                padding: 10px;
                border: none;
                font-size: 16px;
            }
            
            QTableWidget::item:selected {
                background-color: #e9ecef;
                color: black;
                border: none;
            }
            
            QTableWidget::item:focus {
                background-color: #e9ecef;
                border: none;
                outline: none;
            }
            
            QTextEdit, QPlainTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
        """)
    
    def setup_ui(self):
        """设置优化后的UI布局"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 设置整体应用样式
        main_widget.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 16px;
            }
        """)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)  # 减少间距使布局更紧凑
        main_layout.setContentsMargins(15, 15, 15, 15)  # 减少边距使布局更饱满
        
        # 顶部工具栏
        self.create_toolbar(main_layout)
        
        # 主要内容区域
        self.create_main_content(main_layout)
        
        # 生成进度显示区域
        self.create_progress_card(main_layout)
    
    def create_toolbar(self, parent_layout):
        """创建顶部工具栏"""
        # 创建主要的水平布局，左右分区
        main_horizontal_layout = QHBoxLayout()
        main_horizontal_layout.setSpacing(30)  # 增加左右区域间距
        
        # === 左侧区域：标题、状态和风格选择 ===
        left_section = QVBoxLayout()
        left_section.setSpacing(15)
        
        # 第一行：标题和当前模型显示
        title_layout = QHBoxLayout()
        title_label = QLabel("🌊 深海圈生图工具")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50; padding: 8px 0px;")
        title_layout.addWidget(title_label)
        
        
        title_layout.addStretch()
        left_section.addLayout(title_layout)
        
        # 第二行：状态显示
        status_layout = QHBoxLayout()
        self.quick_status_label = QLabel("云雾 | 5线程 | 未设保存路径")
        self.quick_status_label.setStyleSheet("""
            QLabel {
                color: #666; 
                font-size: 18px; 
                padding: 8px 14px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
            }
        """)
        status_layout.addWidget(self.quick_status_label)
        status_layout.addStretch()
        left_section.addLayout(status_layout)
        
        # 第三行：风格选择（移至左侧）
        self.create_style_selection_panel(left_section)
        
        main_horizontal_layout.addLayout(left_section)
        
        # === 右侧区域：API设置、元提示词和设置按钮 ===
        right_section = QVBoxLayout()
        right_section.setSpacing(15)
        
        # API快捷状态和设置按钮
        api_settings_layout = QHBoxLayout()
        api_settings_layout.addStretch()
        
        # API状态显示
        self.api_status_label = QLabel("API: 未配置")
        self.api_status_label.setStyleSheet("""
            QLabel {
                color: #dc3545; 
                font-size: 18px; 
                padding: 8px 14px;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 6px;
                margin-right: 10px;
            }
        """)
        api_settings_layout.addWidget(self.api_status_label)
        
        # 设置按钮
        self.settings_button = QPushButton("设置中心")
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-size: 20px;
                font-weight: 500;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #495057;
            }
        """)
        self.settings_button.clicked.connect(self.open_settings)
        api_settings_layout.addWidget(self.settings_button)
        
        right_section.addLayout(api_settings_layout)
        
        # 元提示词显示区域（完整显示）
        try:
            self.create_full_meta_prompt_display(right_section)
        except Exception as e:
            print(f"元提示词显示创建失败: {e}")
            # 创建一个简单的占位标签
            self.current_meta_prompt_label = QLabel("元提示词未设置")
            right_section.addWidget(self.current_meta_prompt_label)
        
        main_horizontal_layout.addLayout(right_section)
        
        # 设置左右布局比例 (左侧占更多空间)
        main_horizontal_layout.setStretch(0, 3)  # 左侧占60%
        main_horizontal_layout.setStretch(1, 2)  # 右侧占40%
        
        parent_layout.addLayout(main_horizontal_layout)
    
    def create_full_meta_prompt_display(self, parent_layout):
        """创建完整的元提示词显示区域（右侧）"""
        meta_prompt_group = QGroupBox("🤖 AI元提示词配置")
        meta_prompt_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 18px;
                color: #2c3e50;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin: 4px 0px;
                padding-top: 18px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ebf3ff, stop: 1 #d6e9ff);
                min-height: 140px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 8px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                padding: 4px 12px;
                border-radius: 6px;
                color: #2c3e50;
            }
        """)
        
        meta_layout = QVBoxLayout(meta_prompt_group)
        meta_layout.setSpacing(8)
        meta_layout.setContentsMargins(12, 10, 12, 10)
        
        # AI状态和快捷配置按钮
        status_layout = QHBoxLayout()
        
        # AI状态指示
        self.ai_status_label = QLabel("状态: 未启用")
        self.ai_status_label.setStyleSheet("""
            QLabel {
                color: #6c757d; 
                font-size: 16px;
                font-weight: 500;
                padding: 6px 10px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        status_layout.addWidget(self.ai_status_label)
        
        status_layout.addStretch()
        
        # 快捷配置按钮
        self.quick_optimize_button = QPushButton("⚡ 快速配置")
        self.quick_optimize_button.setToolTip("快捷配置 AI 优化")
        self.quick_optimize_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-size: 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.quick_optimize_button.clicked.connect(self.open_ai_settings)
        status_layout.addWidget(self.quick_optimize_button)
        
        meta_layout.addLayout(status_layout)
        
        # 元提示词显示区域（完整内容）
        meta_content_frame = QFrame()
        meta_content_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        meta_content_layout = QVBoxLayout(meta_content_frame)
        meta_content_layout.setContentsMargins(6, 4, 6, 4)
        
        # AI模型显示
        model_title = QLabel("模型:")
        model_title.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 2px;
            }
        """)
        meta_content_layout.addWidget(model_title)
        
        self.current_model_label = QLabel("未设置")
        self.current_model_label.setStyleSheet("""
            QLabel {
                color: #007bff;
                font-size: 14px;
                font-weight: 500;
                padding: 2px;
            }
        """)
        meta_content_layout.addWidget(self.current_model_label)
        
        # 元提示词片段显示
        prompt_title = QLabel("提示词:")
        prompt_title.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 2px;
                margin-top: 4px;
            }
        """)
        meta_content_layout.addWidget(prompt_title)
        
        self.current_meta_prompt_label = QLabel("尚未设置")
        self.current_meta_prompt_label.setWordWrap(True)  # 支持换行
        self.current_meta_prompt_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.current_meta_prompt_label.setMaximumHeight(45)  # 足够显示更多prompt内容
        self.current_meta_prompt_label.setStyleSheet("""
            QLabel {
                color: #212529;
                font-size: 13px;
                line-height: 1.2;
                background: transparent;
                border: none;
                padding: 2px;
            }
        """)
        meta_content_layout.addWidget(self.current_meta_prompt_label)
        
        meta_layout.addWidget(meta_content_frame)
        
        parent_layout.addWidget(meta_prompt_group)
    
    def create_style_selection_panel(self, parent_layout):
        """创建风格选择面板（左侧）"""
        style_group = QGroupBox("🎨 风格选择")
        style_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #2c3e50;
                border: 2px solid #e67e22;
                border-radius: 6px;
                margin: 3px 0px;
                padding-top: 15px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #fef9e7, stop: 1 #fcf4dd);
                min-height: 95px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                top: 8px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
                padding: 4px 12px;
                border-radius: 6px;
                color: #2c3e50;
            }
        """)
        
        style_layout = QVBoxLayout(style_group)
        style_layout.setSpacing(6)
        style_layout.setContentsMargins(12, 8, 12, 8)
        
        # 风格选择下拉框
        style_selection_layout = QHBoxLayout()
        
        style_label = QLabel("当前:")
        style_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 14px;
                font-weight: 600;
                min-width: 50px;
            }
        """)
        style_selection_layout.addWidget(style_label)
        
        self.main_style_combo = QComboBox()
        self.main_style_combo.setMinimumWidth(180)
        self.main_style_combo.setStyleSheet("""
            QComboBox {
                padding: 5px 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
                max-height: 26px;
            }
            QComboBox:hover {
                border-color: #e67e22;
            }
            QComboBox:focus {
                border-color: #e67e22;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #6c757d;
            }
        """)
        self.main_style_combo.currentTextChanged.connect(self.on_main_style_changed)
        style_selection_layout.addWidget(self.main_style_combo)
        
        style_layout.addLayout(style_selection_layout)
        
        # 风格描述预览
        style_preview_label = QLabel("风格描述:")
        style_preview_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 14px;
                font-weight: 600;
                margin-top: 8px;
            }
        """)
        style_layout.addWidget(style_preview_label)
        
        # 风格描述预览（紧凑版）
        self.style_preview_text = QLabel("请选择一个风格")
        self.style_preview_text.setWordWrap(True)
        self.style_preview_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.style_preview_text.setMaximumHeight(30)  # 足够显示内容的高度
        self.style_preview_text.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
                line-height: 1.2;
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-radius: 2px;
                padding: 4px 6px;
            }
        """)
        style_layout.addWidget(self.style_preview_text)
        
        parent_layout.addWidget(style_group)
    
    def create_button_group(self, title, buttons):
        """创建按钮组 - 现代化设计"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #555;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                margin: 8px 4px;
                padding-top: 18px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8f9fa);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                top: 6px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f5f5f5);
                color: #666;
                padding: 2px 8px;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(3)
        layout.setContentsMargins(6, 4, 6, 6)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        
        for i, (text, callback, color) in enumerate(buttons):
            button = QPushButton(text)
            button.clicked.connect(callback)
            
            # 设置按钮的对象名用于后续查找
            if "全选" in text:
                button.setObjectName("全选按钮")
            elif "优化" in text:
                button.setObjectName("优化按钮")
            elif "智能生成" in text:
                button.setObjectName("生成按钮")
            elif "重新生成" in text:
                button.setObjectName("重生成按钮")
            
            # 自适应按钮样式 - 根据文字长度调整宽度
            text_length = len(text)
            if text_length <= 4:
                width = "60px"
            elif text_length <= 6:
                width = "80px"
            else:
                width = "100px"
                
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: 1px solid {color};
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: {width};
                    min-height: 28px;
                    max-height: 32px;
                }}
                QPushButton:hover {{
                    background-color: {color};
                    border: 1px solid white;
                    opacity: 0.9;
                }}
                QPushButton:pressed {{
                    background-color: {color};
                    opacity: 0.8;
                }}
            """)
            
            button_layout.addWidget(button)
        
        layout.addLayout(button_layout)
        return group
    
    def darken_color(self, hex_color, factor=0.2):
        """使颜色变暗"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * (1 - factor)) for c in rgb)
        return '#' + ''.join(f'{c:02x}' for c in darkened)
    
    def lighten_color(self, hex_color, factor=0.1):
        """使颜色变亮"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lightened = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return '#' + ''.join(f'{c:02x}' for c in lightened)
    
    def get_button_from_group(self, group, keyword):
        """从按钮组中获取包含关键词的按钮"""
        for button in group.findChildren(QPushButton):
            if keyword in button.text():
                return button
        return None
    
    def create_main_content(self, parent_layout):
        """创建主要内容区域"""
        main_card = QGroupBox("📝 提示词管理与生成")
        main_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 18px;
                color: #2c3e50;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 12px 4px;
                padding-top: 24px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #fafafa);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 18px;
                top: 10px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                padding: 4px 12px;
                border-radius: 6px;
                color: #2c3e50;
            }
        """)
        parent_layout.addWidget(main_card)
        
        layout = QVBoxLayout(main_card)
        
        # 元提示词区域已移至右上角
        
        # 现代化分组工具栏设计
        toolbar_container = QFrame()
        toolbar_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 20px;
                margin: 8px 0px;
            }
        """)
        
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setSpacing(12)  # 进一步减小组间距离
        
        # === 文件操作区 ===
        file_group = self.create_button_group("文件操作", [
            ("导入CSV", self.import_csv, "#2196F3"),
            ("导出CSV", self.export_prompts_to_csv, "#2196F3")
        ])
        toolbar_layout.addWidget(file_group)
        
        # === 内容编辑区 ===
        edit_group = self.create_button_group("内容编辑", [
            ("添加", self.add_prompt, "#4CAF50"),
            ("删除选中", self.delete_selected_prompts, "#F44336"),
            ("清空", self.clear_prompts, "#F44336"),
            ("清除参考图", self.clear_selected_reference_images, "#FF9800"),
            ("全选", self.toggle_select_all, "#607D8B")
        ])
        toolbar_layout.addWidget(edit_group)
        
        # === AI功能区 ===
        ai_group = self.create_button_group("AI功能", [
            ("文字替换", self.open_text_replace_dialog, "#FF9800"),
            ("批量优化", self.batch_optimize_prompts, "#9C27B0")
        ])
        toolbar_layout.addWidget(ai_group)
        
        # === 生成控制区 ===
        generate_group = self.create_button_group("图片生成", [
            ("智能生成", self.start_generation, "#4CAF50"),
            ("重新生成", self.start_regenerate_all, "#FF5722")
        ])
        toolbar_layout.addWidget(generate_group)
        
        # 存储按钮引用供后续使用 - 通过返回的按钮组获取
        self.select_all_button = self.get_button_from_group(edit_group, "全选")
        self.batch_optimize_button = self.get_button_from_group(ai_group, "批量优化") 
        self.generate_button = self.get_button_from_group(generate_group, "智能生成")
        self.regenerate_all_button = self.get_button_from_group(generate_group, "重新生成")
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(toolbar_container)
        button_layout.addStretch()
        
        # 风格选择已移至左侧面板，此处删除
        
        # 底部信息栏
        info_layout = QHBoxLayout()
        
        # 使用提示
        usage_hint = QLabel("💡 双击提示词可编辑")
        usage_hint.setStyleSheet("""
            QLabel {
                color: #6c757d; 
                font-size: 14px; 
                font-style: italic;
                padding: 6px 10px;
                background-color: #f8f9fa;
                border-radius: 4px;
            }
        """)
        info_layout.addWidget(usage_hint)
        
        info_layout.addStretch()
        
        # 统计信息
        self.prompt_stats_label = QLabel("总计: 0 个提示词")
        self.prompt_stats_label.setStyleSheet("""
            QLabel {
                color: #495057; 
                font-size: 16px;
                font-weight: 600;
                padding: 8px 14px;
                background-color: #e9ecef;
                border-radius: 6px;
            }
        """)
        info_layout.addWidget(self.prompt_stats_label)
        
        button_layout.addLayout(info_layout)
        
        layout.addLayout(button_layout)
        
        # 提示词表格（支持拖拽）
        self.prompt_table = DragDropTableWidget()
        self.prompt_table.set_main_window(self)
        self.prompt_table.setColumnCount(8)
        self.prompt_table.setHorizontalHeaderLabels(["选择", "编号", "提示词", "参考图", "图库", "生成状态/图片", "AI优化", "单独生成"])
        
        # 设置表格属性
        self.prompt_table.setAlternatingRowColors(False)  # 禁用斑马纹，全部白色背景
        self.prompt_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)  # 整行选择
        
        # 启用拖拽功能
        self.prompt_table.setAcceptDrops(True)
        self.prompt_table.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.prompt_table.setDefaultDropAction(Qt.DropAction.CopyAction)
        
        # 现代化表格样式
        self.prompt_table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                gridline-color: #f0f0f0;
                selection-background-color: #e3f2fd;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f5f5f5;
                border-right: 1px solid #f5f5f5;
            }
            QTableWidget::item:selected {
                background-color: #cce7ff;
                color: #0056b3;
                border: 2px solid #007bff;
                font-weight: 600;
            }
            QTableWidget::item:hover {
                background-color: #f0f8ff;
                border: 1px solid #b3d9ff;
            }
            QTableWidget::item:focus {
                background-color: #e6f3ff;
                border: 2px solid #007bff;
                outline: none;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                color: #495057;
                padding: 12px 8px;
                border: none;
                border-right: 1px solid #dee2e6;
                border-bottom: 1px solid #dee2e6;
                font-weight: 600;
                font-size: 16px;
            }
            QHeaderView::section:first {
                border-top-left-radius: 8px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 8px;
                border-right: none;
            }
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9ecef, stop:1 #dee2e6);
            }
        """)
        # 允许多种编辑触发方式：双击、单击、F2键
        self.prompt_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | 
            QAbstractItemView.EditTrigger.EditKeyPressed |
            QAbstractItemView.EditTrigger.SelectedClicked
        )
        
        # 设置表格图标尺寸（重要：这决定了缩略图在表格中的显示大小）
        self.prompt_table.setIconSize(QSize(180, 180))
        
        
        # 设置列宽
        header = self.prompt_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 选择列固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # 编号列固定宽度
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 提示词列自适应
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # 参考图列固定宽度
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # 图库列固定宽度
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # 生成状态/图片列固定宽度
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # AI优化列固定宽度
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # 单独生成列固定宽度
        
        self.prompt_table.setColumnWidth(0, 60)   # 选择列
        self.prompt_table.setColumnWidth(1, 70)   # 编号列
        self.prompt_table.setColumnWidth(3, 100)  # 参考图列
        self.prompt_table.setColumnWidth(4, 90)   # 图库列（缩小）
        self.prompt_table.setColumnWidth(5, 200)  # 生成状态/图片列（合并后加宽）
        self.prompt_table.setColumnWidth(6, 90)   # AI优化列
        self.prompt_table.setColumnWidth(7, 90)   # 单独生成列
        
        # 设置行高自适应内容
        self.prompt_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.prompt_table.verticalHeader().setMinimumSectionSize(230)  # 设置最小行高为230像素
        
        # 隐藏行号，避免与编号列混淆
        self.prompt_table.verticalHeader().setVisible(False)
        
        # 设置文本换行
        self.prompt_table.setWordWrap(True)
        
        # 设置自定义委托
        self.table_delegate = PromptTableDelegate(main_window=self)
        self.prompt_table.setItemDelegate(self.table_delegate)
        
        # 连接信号（提示词列现在使用内嵌编辑器，不需要cellChanged）
        self.prompt_table.cellDoubleClicked.connect(self.on_table_cell_double_clicked)
        self.prompt_table.cellClicked.connect(self.on_table_cell_clicked)
        
        layout.addWidget(self.prompt_table)
    
    def on_checkbox_changed(self, state, row):
        """处理复选框状态变化"""
        
        # 更新行的背景色
        if state == 2:  # 选中状态
            for col in range(self.prompt_table.columnCount()):
                item = self.prompt_table.item(row, col)
                if item:
                    item.setBackground(QColor("#e6f3ff"))  # 淡蓝色背景
        else:  # 未选中状态
            for col in range(self.prompt_table.columnCount()):
                item = self.prompt_table.item(row, col)
                if item:
                    item.setBackground(QColor("#ffffff"))  # 白色背景
        
        # 更新批量优化按钮状态
        self.update_batch_optimize_button()
    
    def create_progress_card(self, parent_layout):
        """创建生成进度显示卡片"""
        progress_card = QGroupBox("📊 生成进度")
        progress_card.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 18px;
                color: #2c3e50;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin: 4px 0px;
                padding-top: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                max-height: 80px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                top: 8px;
                background-color: transparent;
                color: #2c3e50;
            }
        """)
        parent_layout.addWidget(progress_card)
        
        layout = QVBoxLayout(progress_card)
        
        # 进度信息
        self.overall_progress_label = QLabel("等待开始...")
        self.overall_progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overall_progress_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; padding: 4px;")
        layout.addWidget(self.overall_progress_label)
        
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setVisible(False)
        layout.addWidget(self.overall_progress_bar)
        
        # 提示词统计
        self.prompt_stats_label = QLabel("")
        self.prompt_stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_stats_label.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(self.prompt_stats_label)
    
    def open_settings(self):
        """打开设置中心"""
        dialog = SettingsDialog(self)
        dialog.exec()
    
    def open_ai_settings(self):
        """直接打开AI优化配置标签页"""
        dialog = SettingsDialog(self)
        # 切换到AI优化标签页 (索引3: 基础配置0, 风格库1, 参考图库2, AI优化3)
        dialog.tab_widget.setCurrentIndex(3)
        dialog.exec()
    
    def refresh_ui_after_settings(self):
        """设置应用后刷新界面"""
        try:
            # 更新快捷状态显示
            if hasattr(self, 'quick_status_label'):
                save_status = "已设置" if self.save_path else "未设置"
                self.quick_status_label.setText(f"API平台: {self.api_platform} | 线程: {self.thread_count} | 保存路径: {save_status}")
            
            # 更新生图模型显示
            self.on_model_changed(self.image_model)
            
            # 更新API状态显示
            if hasattr(self, 'api_status_label'):
                api_key = self.get_current_api_key()
                if api_key and api_key.strip():
                    # 根据模型显示不同的emoji和颜色
                    if self.image_model == "sora":
                        model_emoji = "🌊"
                        model_color = "#17a2b8"
                    elif self.image_model == "nano-banana":
                        model_emoji = "🍌" 
                        model_color = "#fd7e14"
                    else:
                        model_emoji = "🤖"
                        model_color = "#28a745"
                    
                    self.api_status_label.setText(f"{model_emoji} {self.image_model} 模型 | {self.api_platform} 平台")
                    self.api_status_label.setStyleSheet(f"""
                        QLabel {{
                            color: #ffffff; 
                            font-size: 14px; 
                            font-weight: bold;
                            padding: 8px 14px;
                            background-color: {model_color};
                            border: 2px solid rgba(255, 255, 255, 0.3);
                            border-radius: 8px;
                            margin-right: 10px;
                        }}
                    """)
                else:
                    self.api_status_label.setText("❌ API未配置")
                    self.api_status_label.setStyleSheet("""
                        QLabel {
                            color: #dc3545; 
                            font-size: 14px; 
                            padding: 8px 14px;
                            background-color: #f8d7da;
                            border: 1px solid #f5c6cb;
                            border-radius: 6px;
                            margin-right: 10px;
                        }
                    """)
            
            # 更新AI优化显示
            if hasattr(self, 'update_ai_optimization_display'):
                self.update_ai_optimization_display()
            
            # 刷新主界面的风格选择下拉框
            if hasattr(self, 'main_style_combo') and hasattr(self, 'refresh_main_style_combo'):
                self.refresh_main_style_combo()
                
        except Exception as e:
            # 如果UI刷新失败，记录但不影响程序运行
            print(f"UI刷新失败: {e}")
            pass
    
    def update_ai_optimization_display(self):
        """更新AI优化显示信息"""
        try:
            if hasattr(self, 'current_meta_prompt_label') and hasattr(self, 'ai_status_label'):
                # 更新AI模型显示
                if hasattr(self, 'current_model_label'):
                    if self.openrouter_api_key.strip():
                        # 显示模型名称（简化显示）
                        model_display = self.ai_model.split('/')[-1] if '/' in self.ai_model else self.ai_model
                        self.current_model_label.setText(model_display)
                    else:
                        self.current_model_label.setText("未设置")
                
                # 更新元提示词显示（显示更多内容）
                if self.meta_prompt.strip():
                    # 显示前80个字符，保持关键信息
                    preview_text = self.meta_prompt.strip()[:80] + "..." if len(self.meta_prompt.strip()) > 80 else self.meta_prompt.strip()
                    self.current_meta_prompt_label.setText(preview_text)
                else:
                    self.current_meta_prompt_label.setText("尚未设置")
                
                # 更新AI状态显示
                if self.openrouter_api_key.strip():
                    self.ai_status_label.setText(f"AI优化: 已配置 ({self.ai_model})")
                    self.ai_status_label.setStyleSheet("color: #4caf50; font-size: 14px;")
                else:
                    self.ai_status_label.setText("AI优化: 未配置")
                    self.ai_status_label.setStyleSheet("color: #666; font-size: 14px;")
                    
            # 刷新提示词表格中的AI优化按钮状态
            if hasattr(self, 'refresh_prompt_table'):
                self.refresh_prompt_table()
        except Exception as e:
            # 如果AI优化显示更新失败，记录但不影响程序运行
            print(f"AI优化显示更新失败: {e}")
            pass
    
    def import_csv(self):
        """导入CSV文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择CSV文件",
            "",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # 尝试不同的编码方式读取CSV文件
                encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    QMessageBox.critical(self, "错误", "无法读取CSV文件，请确保文件编码为UTF-8、GBK、GB2312或GB18030")
                    return
                
                # 检查是否存在"分镜提示词"列
                if "分镜提示词" not in df.columns:
                    QMessageBox.critical(self, "错误", "CSV文件中没有找到'分镜提示词'列")
                    return
                
                # 检查是否存在"分镜编号"列
                has_number_column = "分镜编号" in df.columns
                
                # 清空现有数据
                self.prompt_table_data.clear()
                self.prompt_numbers.clear()
                
                # 添加提示词到数据
                for index, row in df.iterrows():
                    prompt = row["分镜提示词"]
                    if pd.notna(prompt):
                        prompt_str = str(prompt)
                        
                        # 确定编号
                        if has_number_column:
                            number = row["分镜编号"]
                            if pd.notna(number):
                                display_number = str(number)
                            else:
                                display_number = str(index + 1)
                        else:
                            display_number = str(index + 1)
                        
                        # 添加到数据列表
                        self.prompt_table_data.append({
                            'number': display_number,
                            'prompt': prompt_str,
                            'status': '等待中',
                            'image_url': '',
                            'error_msg': '',
                            'reference_images': []  # 改为支持多张参考图片的列表
                        })
                        
                        self.prompt_numbers[prompt_str] = display_number
                
                # 刷新表格显示
                self.refresh_prompt_table()
                self.update_prompt_stats()
                QMessageBox.information(self, "成功", f"成功导入 {len(self.prompt_table_data)} 个提示词")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入CSV文件失败: {str(e)}")
    
    def clear_prompts(self):
        """清空导入的提示词列表"""
        self.prompt_table_data.clear()
        self.prompt_numbers.clear()
        self.refresh_prompt_table()
        self.update_prompt_stats()
        QMessageBox.information(self, "完成", "已清空所有提示词")
    
    def export_prompts_to_csv(self):
        """导出提示词到CSV文件"""
        if not self.prompt_table_data:
            QMessageBox.warning(self, "提示", "没有可导出的提示词数据")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出提示词",
            f"sora_prompts_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                import pandas as pd
                
                # 准备导出数据
                export_data = []
                for data in self.prompt_table_data:
                    export_data.append({
                        '编号': data['number'],
                        '提示词': data['prompt'],
                        '状态': data['status'],
                        '错误信息': data.get('error_msg', ''),
                        '图片URL': data.get('image_url', '')
                    })
                
                # 创建DataFrame并导出
                df = pd.DataFrame(export_data)
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                QMessageBox.information(self, "导出成功", 
                    f"已成功导出 {len(export_data)} 个提示词到:\n{file_path}")
                
            except ImportError:
                QMessageBox.critical(self, "导出失败", "缺少pandas模块，无法导出CSV文件")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出过程中出现错误: {str(e)}")
    
    def open_text_replace_dialog(self):
        """打开文字替换对话框"""
        if not self.prompt_table_data:
            QMessageBox.warning(self, "提示", "没有提示词数据，请先添加提示词或导入CSV文件")
            return
        
        dialog = TextReplaceDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            replacement_data = dialog.get_replacement_data()
            find_text = replacement_data['find_text']
            replace_text = replacement_data['replace_text']
            
            if not find_text:
                QMessageBox.warning(self, "提示", "请输入要查找的文字")
                return
            
            # 执行替换
            replaced_count = 0
            for data in self.prompt_table_data:
                if find_text in data['prompt']:
                    data['prompt'] = data['prompt'].replace(find_text, replace_text)
                    replaced_count += 1
            
            if replaced_count > 0:
                # 刷新表格显示
                self.refresh_prompt_table()
                QMessageBox.information(self, "替换完成", 
                    f"成功替换了 {replaced_count} 个提示词中的文字")
            else:
                QMessageBox.information(self, "替换完成", "未找到匹配的文字，没有进行替换")
    
    def open_gallery_dialog(self, row):
        """打开图库选择对话框"""
        if not self.category_links:
            QMessageBox.warning(self, "提示", "图库为空，请先在设置中心配置参考图库")
            return
        
        if 0 <= row < len(self.prompt_table_data):
            # 清理无效的编辑器引用
            self.clean_inactive_editors()
            
            dialog = GallerySelectionDialog(self.category_links, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_image = dialog.get_selected_image()
                if selected_image:
                    # 如果是字典，获取name字段；如果是字符串，直接使用
                    if isinstance(selected_image, dict):
                        image_name_raw = selected_image.get('name', selected_image)
                    else:
                        image_name_raw = selected_image
                    
                    # 用「」框起来
                    image_name = f"「{image_name_raw}」"
                    
                    # 现在所有提示词都有持续活跃的编辑器，直接插入
                    if row in self.active_editors:
                        editor = self.active_editors[row]
                        try:
                            if isinstance(editor, QLineEdit):
                                cursor_pos = editor.cursorPosition()
                                current_text = editor.text()
                                new_text = current_text[:cursor_pos] + image_name + current_text[cursor_pos:]
                                editor.setText(new_text)
                                # 移动光标到插入文本之后
                                new_cursor_pos = cursor_pos + len(image_name)
                                editor.setCursorPosition(new_cursor_pos)
                                # 确保焦点在这个编辑器上
                                editor.setFocus()
                                self.focused_row = row
                                return
                            elif isinstance(editor, QPlainTextEdit):
                                cursor = editor.textCursor()
                                cursor_pos = cursor.position()
                                # 使用insertText方法保持撤销历史
                                cursor.insertText(image_name)
                                editor.setTextCursor(cursor)
                                # 确保焦点在这个编辑器上
                                editor.setFocus()
                                self.focused_row = row
                                return
                        except (RuntimeError, AttributeError):
                            # 编辑器已被删除或不可用，从活跃编辑器列表中移除
                            if row in self.active_editors:
                                del self.active_editors[row]
                    
                    # 如果编辑器不可用，作为后备方案更新数据模型
                    current_prompt = self.prompt_table_data[row]['prompt']
                    cursor_pos = self.get_smart_cursor_position(row)
                    cursor_pos = min(cursor_pos, len(current_prompt))
                    new_prompt = current_prompt[:cursor_pos] + image_name + current_prompt[cursor_pos:]
                    self.prompt_table_data[row]['prompt'] = new_prompt
                    # 重建编辑器
                    prompt_editor = self.create_prompt_editor(new_prompt, row)
                    self.prompt_table.setCellWidget(row, 2, prompt_editor)
                    # 设置光标到插入位置之后
                    new_cursor_pos = cursor_pos + len(image_name)
                    if isinstance(prompt_editor, QLineEdit):
                        prompt_editor.setCursorPosition(new_cursor_pos)
                    else:
                        cursor = prompt_editor.textCursor()
                        cursor.setPosition(new_cursor_pos)
                        prompt_editor.setTextCursor(cursor)
                    prompt_editor.setFocus()
    
    def record_cursor_position(self, row, position):
        """记录指定行的光标位置"""
        if row >= 0 and position >= 0:
            self.cursor_positions[row] = position
    
    def set_active_editor(self, row, editor):
        """设置当前活跃的编辑器"""
        self.active_editors[row] = editor
        
    def clean_inactive_editors(self):
        """清理无效的编辑器引用"""
        to_remove = []
        for row, editor in self.active_editors.items():
            try:
                # 尝试访问编辑器的一个属性来测试是否还有效
                if isinstance(editor, QLineEdit):
                    _ = editor.text()
                elif isinstance(editor, QPlainTextEdit):
                    _ = editor.toPlainText()
            except (RuntimeError, AttributeError):
                to_remove.append(row)
        
        for row in to_remove:
            del self.active_editors[row]
    
    def get_current_cursor_position(self, row):
        """获取指定行的当前光标位置"""
        # 优先从活跃编辑器获取实时光标位置
        if row in self.active_editors:
            editor = self.active_editors[row]
            try:
                if isinstance(editor, QLineEdit):
                    return editor.cursorPosition()
                elif isinstance(editor, QPlainTextEdit):
                    return editor.textCursor().position()
            except (RuntimeError, AttributeError):
                # 编辑器已无效，清理并使用记录的位置
                if row in self.active_editors:
                    del self.active_editors[row]
        
        # 如果没有活跃编辑器，使用记录的位置
        return self.cursor_positions.get(row, 0)
        
    def get_smart_cursor_position(self, row):
        """获取智能光标位置 - 专为图片插入优化"""
        # 如果当前行正是焦点行，尝试从活跃编辑器获取最新位置
        if row == self.focused_row and row in self.active_editors:
            editor = self.active_editors[row]
            try:
                if isinstance(editor, QLineEdit):
                    pos = editor.cursorPosition()
                    # 更新记录的位置
                    self.cursor_positions[row] = pos
                    return pos
                elif isinstance(editor, QPlainTextEdit):
                    pos = editor.textCursor().position()
                    # 更新记录的位置
                    self.cursor_positions[row] = pos
                    return pos
            except (RuntimeError, AttributeError):
                # 编辑器已无效，清理
                if row in self.active_editors:
                    del self.active_editors[row]
        
        # 使用记录的位置，如果没有记录则使用文本末尾
        if row < len(self.prompt_table_data):
            text_length = len(self.prompt_table_data[row]['prompt'])
            return self.cursor_positions.get(row, text_length)
        
        return 0
    
    def create_prompt_editor(self, text, row):
        """创建提示词的内嵌编辑器"""
        # 统一使用QPlainTextEdit，支持自动换行和滚动
        editor = QPlainTextEdit()
        editor.setPlainText(text)
        
        # 应用所有样式和设置
        self.apply_editor_settings(editor)
        
        # 连接信号处理文本变化
        def handle_text_change(r=row, e=editor):
            self.on_prompt_text_changed(r, e.toPlainText())
        def handle_cursor_change(r=row, e=editor):
            self.on_cursor_position_changed(r, e.textCursor().position())
        
        editor.textChanged.connect(handle_text_change)
        editor.cursorPositionChanged.connect(handle_cursor_change)
        
        # 添加动态高度调整
        def adjust_height():
            self.adjust_editor_height(editor)
        editor.textChanged.connect(adjust_height)
        
        # 初始调整高度
        self.adjust_editor_height(editor)
        
        # 注册为活跃编辑器
        self.active_editors[row] = editor
        
        return editor
    
    def apply_editor_settings(self, editor):
        """应用编辑器的样式和设置"""
        if not isinstance(editor, QPlainTextEdit):
            return
        
        # 设置自动换行
        editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        
        # 设置尺寸策略 - 让编辑器填满整个单元格
        editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 确保编辑器占用全部可用宽度
        editor.setMinimumWidth(200)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 设置文档边距为0，让文本填充到边沿
        editor.document().setDocumentMargin(0)
        editor.setContentsMargins(0, 0, 0, 0)
        
        # 设置视口边距为0
        editor.setViewportMargins(0, 0, 0, 0)
        
        # 获取文档并设置更详细的边距控制
        doc = editor.document()
        doc.setDocumentMargin(0)
        
        # 设置文本光标边距
        editor.setCursorWidth(1)
        
        # 设置合理的高度范围
        editor.setMinimumHeight(200)  # 调整最小高度到200像素
        editor.setMaximumHeight(450)
        
        # 应用样式
        editor.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 0px !important;
                margin: 0px !important;
                background-color: white;
                font-size: 20px;
                line-height: 1.2;
                font-weight: 500;
                font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
                width: 100%;
                min-width: 100%;
                padding-top: 0px !important;
                padding-bottom: 0px !important;
                padding-left: 0px !important;
                padding-right: 0px !important;
                selection-background-color: #3399ff;
            }
            QPlainTextEdit:focus {
                border: 2px solid #1976d2;
                background-color: #fafafa;
                padding: 0px !important;
                margin: 0px !important;
            }
            QPlainTextEdit QScrollArea {
                padding: 0px !important;
                margin: 0px !important;
            }
            QPlainTextEdit QAbstractScrollArea {
                padding: 0px !important;
                margin: 0px !important;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                border: none;
                background: none;
            }
        """)
        
        # 强制刷新样式和布局
        editor.update()
        editor.repaint()
        
        # 调整高度
        self.adjust_editor_height(editor)
    
    def adjust_editor_height(self, editor):
        """根据内容动态调整编辑器高度"""
        if not isinstance(editor, QPlainTextEdit):
            return
        
        try:
            # 获取文档高度
            doc = editor.document()
            doc_height = doc.size().height()
            
            # 计算需要的高度（不加任何边距，让文本充满到边沿）
            border_width = 2  # 边框宽度
            needed_height = int(doc_height + border_width)
            
            # 限制在最小和最大高度之间，但确保文本能完全显示
            min_height = max(200, needed_height)   # 最小高度至少要能显示完整文本
            max_height = 450  # 最大高度
            new_height = min(max_height, min_height)
            
            editor.setFixedHeight(new_height)
            
        except Exception as e:
            # 如果出错，使用默认高度
            editor.setFixedHeight(100)
    
    def on_prompt_text_changed(self, row, text):
        """提示词文本改变时的处理"""
        if 0 <= row < len(self.prompt_table_data):
            self.prompt_table_data[row]['prompt'] = text
    
    def on_cursor_position_changed(self, row, position):
        """光标位置改变时的处理"""
        self.record_cursor_position(row, position)
        self.focused_row = row
    
    
    def refresh_main_style_combo(self):
        """刷新主界面的风格选择下拉框"""
        # 阻止信号触发，避免循环调用
        self.main_style_combo.blockSignals(True)
        
        current_text = self.main_style_combo.currentText()
        
        self.main_style_combo.clear()
        self.main_style_combo.addItem("选择风格...")
        
        for style_name in self.style_library.keys():
            self.main_style_combo.addItem(style_name)
        
        # 优先使用当前配置的风格，然后是之前的选择
        target_style = None
        if self.current_style and self.current_style in self.style_library:
            target_style = self.current_style
        elif current_text and current_text != "选择风格..." and current_text in self.style_library:
            target_style = current_text
        
        if target_style:
            self.main_style_combo.setCurrentText(target_style)
        else:
            self.main_style_combo.setCurrentIndex(0)  # 选择"选择风格..."
        
        # 恢复信号
        self.main_style_combo.blockSignals(False)
    
    def on_main_style_changed(self, style_name):
        """主界面风格选择变化处理"""
        if style_name == "选择风格..." or style_name == "":
            self.current_style = ""
            self.custom_style_content = ""
            # 更新风格预览
            if hasattr(self, 'style_preview_text'):
                self.style_preview_text.setText("请选择一个风格")
        else:
            if style_name in self.style_library:
                self.current_style = style_name
                self.custom_style_content = self.style_library[style_name]['content']
                
                # 更新使用次数
                self.style_library[style_name]['usage_count'] = self.style_library[style_name].get('usage_count', 0) + 1
                
                # 更新风格预览
                if hasattr(self, 'style_preview_text'):
                    preview_text = self.custom_style_content
                    # 缩短显示文本，但保留关键信息
                    if len(preview_text) > 60:
                        preview_text = preview_text[:60] + "..."
                    self.style_preview_text.setText(preview_text)
        
        # 保存配置
        self.save_config()
    
    def handle_image_drop(self, image_files, drop_row):
        """处理图片拖拽事件 - 只添加到参考图列"""
        try:
            # 如果拖拽到空白区域（超出现有行范围），创建新行
            if drop_row >= len(self.prompt_table_data):
                # 创建新行，提示词保持默认值，只添加参考图
                max_number = 0
                for data in self.prompt_table_data:
                    try:
                        num = int(data['number'])
                        max_number = max(max_number, num)
                    except ValueError:
                        continue
                
                new_number = str(max_number + 1)
                new_data = {
                    'number': new_number,
                    'prompt': '新提示词',  # 保持默认提示词
                    'status': '等待中',
                    'image_url': '',
                    'error_msg': '',
                    'reference_images': list(image_files)  # 直接设置参考图片列表
                }
                self.prompt_table_data.append(new_data)
            
            elif drop_row >= 0:
                # 添加到现有行的参考图列表
                data = self.prompt_table_data[drop_row]
                existing_images = data.get('reference_images', [])
                existing_images.extend(image_files)
                data['reference_images'] = existing_images
            
            # 刷新表格显示
            self.refresh_prompt_table()
            
            # 显示简单的成功提示
            if len(image_files) == 1:
                image_name = os.path.basename(image_files[0])
                print(f"参考图片已添加: {image_name}")
            else:
                print(f"已添加 {len(image_files)} 张参考图片")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理拖拽图片时出错: {str(e)}")
    
    def add_image_reference_prompt(self, image_path, insert_row=None):
        """添加图片参考提示词（此方法现在用于其他场景，如果需要）"""
        try:
            # 获取图片文件名（不包括扩展名）
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            
            # 生成新编号
            max_number = 0
            for data in self.prompt_table_data:
                try:
                    num = int(data['number'])
                    max_number = max(max_number, num)
                except ValueError:
                    continue
            
            new_number = str(max_number + 1)
            
            # 创建新的提示词数据
            new_data = {
                'number': new_number,
                'prompt': f'参考图片「{image_name}」',  # 初始提示词
                'status': '等待中',
                'image_url': '',
                'error_msg': '',
                'reference_images': [image_path]  # 保存参考图片路径到列表
            }
            
            # 插入到指定位置或末尾
            if insert_row is not None and 0 <= insert_row < len(self.prompt_table_data):
                self.prompt_table_data.insert(insert_row + 1, new_data)
            else:
                self.prompt_table_data.append(new_data)
                
        except Exception as e:
            raise Exception(f"添加图片参考失败: {str(e)}")
    
    def show_reference_image(self, row, img_index=0):
        """显示参考图片"""
        if 0 <= row < len(self.prompt_table_data):
            data = self.prompt_table_data[row]
            reference_images = data.get('reference_images', [])
            if img_index < len(reference_images):
                image_path = reference_images[img_index]
                if os.path.exists(image_path):
                    dialog = ReferenceImageDialog(image_path, data['prompt'], self)
                    dialog.exec()
                else:
                    QMessageBox.warning(self, "警告", f"参考图片不存在: {image_path}")
    
    def delete_single_reference_image(self, row, img_index):
        """删除单张参考图片"""
        if 0 <= row < len(self.prompt_table_data):
            data = self.prompt_table_data[row]
            reference_images = data.get('reference_images', [])
            
            if 0 <= img_index < len(reference_images):
                img_name = os.path.basename(reference_images[img_index])
                reply = QMessageBox.question(
                    self,
                    "确认删除",
                    f"确定要删除这张参考图片吗？\n\n图片: {img_name}\n\n注意：这只会移除图片关联，不会删除原始文件。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 从列表中删除这张图片
                    reference_images.pop(img_index)
                    data['reference_images'] = reference_images
                    # 刷新表格显示
                    self.refresh_prompt_table()
    
    def add_more_reference_images(self, row):
        """为指定行添加更多参考图片"""
        if 0 <= row < len(self.prompt_table_data):
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "选择参考图片",
                "",
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
            )
            
            if file_paths:
                data = self.prompt_table_data[row]
                reference_images = data.get('reference_images', [])
                
                # 添加新选择的图片
                reference_images.extend(file_paths)
                data['reference_images'] = reference_images
                
                # 刷新表格显示
                self.refresh_prompt_table()
    
    def manage_reference_images(self, row):
        """打开参考图片管理对话框"""
        if 0 <= row < len(self.prompt_table_data):
            data = self.prompt_table_data[row]
            reference_images = data.get('reference_images', [])
            
            if not reference_images:
                QMessageBox.information(self, "提示", "该行没有参考图片")
                return
            
            # 创建管理对话框
            dialog = ReferenceImagesManagerDialog(reference_images, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 更新参考图片列表
                data['reference_images'] = dialog.get_images()
                self.refresh_prompt_table()
    
    def delete_reference_image(self, row):
        """删除所有参考图片（兼容旧版本）"""
        if 0 <= row < len(self.prompt_table_data):
            data = self.prompt_table_data[row]
            reference_images = data.get('reference_images', [])
            
            if reference_images:
                reply = QMessageBox.question(
                    self, 
                    "确认删除", 
                    f"确定要删除第 {row + 1} 行的所有参考图片吗？\n\n共 {len(reference_images)} 张图片\n\n注意：这只会移除图片关联，不会删除原始文件。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # 清除所有参考图片关联
                    data['reference_images'] = []
                    
                    # 刷新表格显示
                    self.refresh_prompt_table()
                    
                    QMessageBox.information(self, "删除成功", f"已删除第 {row + 1} 行的参考图片关联")
    
    def clear_selected_reference_images(self):
        """清除选中行的参考图片"""
        selected_rows = set()
        
        # 优先检查复选框选择
        checkbox_selected = False
        for row in range(len(self.prompt_table_data)):
            checkbox = self.prompt_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_rows.add(row)
                checkbox_selected = True
        
        # 如果没有复选框选择，则检查表格行选择
        if not checkbox_selected:
            for item in self.prompt_table.selectedItems():
                selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要清除参考图的提示词（可以通过复选框选择或点击行选择）")
            return
        
        # 统计有参考图的行数
        rows_with_ref_images = []
        for row in selected_rows:
            if 0 <= row < len(self.prompt_table_data):
                data = self.prompt_table_data[row]
                if data.get('reference_images', []):
                    rows_with_ref_images.append(row)
        
        if not rows_with_ref_images:
            QMessageBox.information(self, "提示", "选中的提示词没有关联的参考图片")
            return
        
        reply = QMessageBox.question(
            self,
            "确认清除",
            f"确定要清除 {len(rows_with_ref_images)} 个提示词的参考图片关联吗？\n\n注意：这只会移除图片关联，不会删除原始文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 清除选中行的参考图片关联
            cleared_count = 0
            for row in rows_with_ref_images:
                if 0 <= row < len(self.prompt_table_data):
                    self.prompt_table_data[row]['reference_images'] = []
                    cleared_count += 1
            
            # 刷新表格显示
            self.refresh_prompt_table()
            self.update_prompt_stats()
            
            QMessageBox.information(self, "清除完成", f"成功清除了 {cleared_count} 个参考图片关联")
    
    def update_prompt_stats(self):
        """更新提示词统计"""
        count = len(self.prompt_table_data)
        reference_count = len([data for data in self.prompt_table_data if data.get('reference_images', [])])
        if reference_count > 0:
            self.prompt_stats_label.setText(f"总计: {count} 个提示词（包含 {reference_count} 个图片参考）")
        else:
            self.prompt_stats_label.setText(f"总计: {count} 个提示词")
    
    def refresh_prompt_table(self):
        """刷新提示词表格显示"""
        # 清理无效的编辑器引用
        self.clean_inactive_editors()
        
        # 清理超出当前数据范围的编辑器
        current_row_count = len(self.prompt_table_data)
        rows_to_remove = [row for row in self.active_editors.keys() if row >= current_row_count]
        for row in rows_to_remove:
            del self.active_editors[row]
        
        self.prompt_table.setRowCount(current_row_count)
        
        for row, data in enumerate(self.prompt_table_data):
            # 选择列 - 复选框
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox {
                    margin: 5px;
                    spacing: 5px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #ced4da;
                    border-radius: 4px;
                    background-color: #ffffff;
                }
                QCheckBox::indicator:hover {
                    border-color: #007bff;
                    background-color: #f8f9ff;
                }
                QCheckBox::indicator:checked {
                    background-color: #007bff;
                    border-color: #007bff;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMS4yNSAwLjc1TDQuNSA3LjUgMC43NSAzLjc1IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjEuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
                }
                QCheckBox::indicator:checked:hover {
                    background-color: #0056b3;
                    border-color: #0056b3;
                }
                QCheckBox::indicator:indeterminate {
                    background-color: #6c757d;
                    border-color: #6c757d;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMiIgdmlld0JveD0iMCAwIDEwIDIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxMCIgaGVpZ2h0PSIyIiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4K);
                }
            """)
            checkbox.stateChanged.connect(lambda state, r=row: self.on_checkbox_changed(state, r))
            self.prompt_table.setCellWidget(row, 0, checkbox)
            
            # 编号列
            number_item = QTableWidgetItem(data['number'])
            number_item.setFlags(number_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 不可编辑
            self.prompt_table.setItem(row, 1, number_item)
            
            # 提示词列 - 强制重新创建编辑器以确保样式正确应用
            # 创建新的编辑器
            prompt_editor = self.create_prompt_editor(data['prompt'], row)
            self.prompt_table.setCellWidget(row, 2, prompt_editor)
            
            
            # 参考图片列 - 简洁信息显示
            reference_images = data.get('reference_images', [])
            if reference_images:
                # 创建简洁的参考图信息widget
                ref_widget = QWidget()
                ref_layout = QVBoxLayout(ref_widget)
                ref_layout.setContentsMargins(4, 4, 4, 4)
                ref_layout.setSpacing(3)
                
                # 图片数量信息
                info_label = QLabel(f"📷 {len(reference_images)} 张图片")
                info_label.setStyleSheet("""
                    QLabel {
                        color: #333;
                        font-size: 12px;
                        font-weight: bold;
                        background-color: #f8f9fa;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 6px;
                        text-align: center;
                    }
                """)
                info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ref_layout.addWidget(info_label)
                
                # 操作按钮
                button_widget = QWidget()
                button_layout = QHBoxLayout(button_widget)
                button_layout.setContentsMargins(0, 0, 0, 0)
                button_layout.setSpacing(3)
                
                # 管理按钮（主要功能）
                manage_button = QPushButton("管理预览")
                manage_button.setStyleSheet("""
                    QPushButton {
                        background-color: #17a2b8;
                        color: white;
                        border: none;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #138496;
                    }
                """)
                manage_button.clicked.connect(lambda checked, r=row: self.manage_reference_images(r))
                
                # 添加按钮
                add_button = QPushButton("添加")
                add_button.setStyleSheet("""
                    QPushButton {
                        background-color: #28a745;
                        color: white;
                        border: none;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #218838;
                    }
                """)
                add_button.clicked.connect(lambda checked, r=row: self.add_more_reference_images(r))
                
                button_layout.addWidget(manage_button)
                button_layout.addWidget(add_button)
                
                ref_layout.addWidget(button_widget)
                
                self.prompt_table.setCellWidget(row, 3, ref_widget)
            else:
                # 清除可能存在的widget并设置空列
                self.prompt_table.setCellWidget(row, 3, None)  # 清除之前的widget
                empty_item = QTableWidgetItem("无参考图")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                empty_item.setForeground(QColor("#999999"))  # 灰色文本
                empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_item.setToolTip("拖拽图片到此行来添加参考图片")
                self.prompt_table.setItem(row, 3, empty_item)
            
            # 图库列 - 添加选择按钮
            gallery_button = QPushButton("选择")
            gallery_button.setToolTip("从图库选择图片")
            gallery_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800;
                    color: white;
                    border: none;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 15px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """)
            gallery_button.clicked.connect(lambda checked, r=row: self.open_gallery_dialog(r))
            self.prompt_table.setCellWidget(row, 4, gallery_button)
            
            # 生成状态/图片列（合并原状态列和图片列）
            status_image_item = QTableWidgetItem()
            status_image_item.setFlags(status_image_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 不可编辑
            status_image_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.prompt_table.setItem(row, 5, status_image_item)
            # 更新合并列的显示内容
            self.update_status_image_display(row, data)
            
            # AI优化列 - 添加优化按钮
            optimize_button = QPushButton("🤖 优化")
            optimize_button.setToolTip("使用AI优化这条提示词")
            optimize_button.setStyleSheet("""
                QPushButton {
                    background-color: #9c27b0;
                    color: white;
                    border: none;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7b1fa2;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                    color: #666;
                }
            """)
            # 检查AI优化是否已配置
            if not self.openrouter_api_key.strip() or not self.meta_prompt.strip():
                optimize_button.setEnabled(False)
                optimize_button.setToolTip("请先在设置中心配置AI优化功能")
            else:
                optimize_button.clicked.connect(lambda checked, r=row: self.optimize_single_prompt(r))
            
            self.prompt_table.setCellWidget(row, 6, optimize_button)
            
            # 单独生成列 - 添加生成按钮
            generate_button = QPushButton("生成")
            generate_button.setToolTip("单独生成这条提示词的图片")
            generate_button.setStyleSheet("""
                QPushButton {
                    background-color: #4caf50;
                    color: white;
                    border: none;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #388e3c;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                    color: #666;
                }
            """)
            # 检查API配置
            if not self.get_current_api_key() or not self.save_path:
                generate_button.setEnabled(False)
                generate_button.setToolTip("请先在设置中心配置API密钥和保存路径")
            else:
                generate_button.clicked.connect(lambda checked, r=row: self.generate_single_prompt(r))
            
            self.prompt_table.setCellWidget(row, 7, generate_button)
            
            # 调整行高以适应内容
            self.prompt_table.resizeRowToContents(row)
    
    def update_status_image_display(self, row, data):
        """更新合并的状态/图片列显示"""
        item = self.prompt_table.item(row, 5)  # 合并后的列索引是5
        if not item:
            return
        
        status = data['status']
        
        if status == '成功':
            # 显示缩略图（从本地文件加载）
            self.load_and_set_thumbnail(row, data['number'])
            item.setBackground(QColor("#e8f5e8"))
        elif status == '失败':
            # 显示失败信息和状态颜色
            error_msg = data.get('error_msg', '生成失败')
            if len(error_msg) > 50:
                error_msg = error_msg[:50] + "..."
            
            item.setText(f"❌ 失败\n{error_msg}")
            item.setToolTip(data.get('error_msg', '生成失败'))
            item.setBackground(QColor("#ffebee"))
            item.setForeground(QColor("#d32f2f"))
            item.setIcon(QIcon())
        elif status == '生成中':
            # 显示进度状态
            item.setText("生成中...")
            item.setBackground(QColor("#e3f2fd"))
            item.setForeground(QColor("#1976d2"))
            item.setIcon(QIcon())
            item.setToolTip("正在生成图片，请等待...")
        elif status == '等待中':
            # 显示等待状态
            item.setText("⏳ 等待中")
            item.setBackground(QColor("#f0f0f0"))
            item.setForeground(QColor("#666"))
            item.setIcon(QIcon())
            item.setToolTip("等待生成")
        else:
            # 其他状态
            item.setText(f"{status}")
            item.setBackground(QColor("#f8f9fa"))
            item.setForeground(QColor("#666"))
            item.setIcon(QIcon())
    
    def update_status_style(self, item, status):
        """更新状态列样式（保留用于兼容性）"""
        if status == "等待中":
            item.setBackground(QColor("#f0f0f0"))
            item.setForeground(QColor("#666"))
        elif status == "生成中":
            item.setBackground(QColor("#e3f2fd"))
            item.setForeground(QColor("#1976d2"))
        elif status == "成功":
            item.setBackground(QColor("#e8f5e8"))
            item.setForeground(QColor("#388e3c"))
        elif status == "失败":
            item.setBackground(QColor("#ffebee"))
            item.setForeground(QColor("#d32f2f"))
    
    def update_image_display(self, row, data):
        """更新图片显示"""
        item = self.prompt_table.item(row, 5)  # 更新列索引：图片列现在是第5列
        if not item:
            return
            
        if data['status'] == '成功':
            # 显示缩略图（从本地文件加载）
            self.load_and_set_thumbnail(row, data['number'])
        elif data['status'] == '失败':
            # 显示详细的失败信息
            error_msg = data.get('error_msg', '生成失败')
            # 简化错误信息，保留关键部分
            if len(error_msg) > 100:
                # 截取关键错误信息
                error_msg = error_msg[:100] + "..."
            
            item.setText(f"❌ 失败:\n{error_msg}")
            item.setToolTip(data.get('error_msg', '生成失败'))  # 完整错误信息作为提示
            item.setForeground(QColor("#d32f2f"))
            item.setIcon(QIcon())  # 清除图标
        else:
            # 其他状态（等待中、生成中等）
            item.setText("")
            item.setIcon(QIcon())  # 清除图标
            item.setToolTip("")
    
    def load_and_set_thumbnail(self, row, image_number):
        """从本地文件加载并设置缩略图"""
        item = self.prompt_table.item(row, 5)  # 使用正确的列索引5
        if not item:
            return
            
        try:
            # 检查保存路径是否设置
            if not self.save_path:
                item.setText("路径未设置")
                item.setToolTip("请先在设置中心配置保存路径")
                item.setForeground(QColor("#ff9800"))
                return
                
            # 从数据中获取实际的文件名
            data = self.prompt_table_data[row] if 0 <= row < len(self.prompt_table_data) else {}
            filename = data.get('filename')
            if not filename:
                # 如果没有文件名，使用旧的命名规则作为后备
                filename = f"{image_number}.png"
            
            file_path = os.path.join(self.save_path, filename)
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                item.setText("文件未找到")
                item.setToolTip(f"本地图片文件不存在: {filename}")
                item.setForeground(QColor("#ff9800"))
                return
            
            # 从本地文件加载图片
            pixmap = QPixmap(file_path)
            
            if not pixmap.isNull():
                # 缩放为缩略图大小（增大尺寸以提高观看体验）
                thumbnail = pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                # 设置图标
                item.setIcon(QIcon(thumbnail))
                item.setText("")
                item.setToolTip("双击查看大图")
            else:
                item.setText("格式错误")
                item.setToolTip(f"图片格式无法识别: {filename}")
                item.setForeground(QColor("#d32f2f"))
            
        except Exception as e:
            error_msg = f"本地缩略图加载失败: {str(e)}"
            
            item.setText("加载失败")
            item.setToolTip(error_msg)
            item.setIcon(QIcon())  # 清除图标
            item.setForeground(QColor("#d32f2f"))
    
    def on_table_cell_clicked(self, row, column):
        """表格单元格点击事件"""
        if column == 2:  # 提示词列 - 现在点击直接聚焦到内嵌编辑器
            if row in self.active_editors:
                editor = self.active_editors[row]
                editor.setFocus()
                self.focused_row = row
    
    def add_prompt(self):
        """添加新提示词"""
        try:
            # 生成新编号
            max_number = 0
            for data in self.prompt_table_data:
                try:
                    num = int(data['number'])
                    max_number = max(max_number, num)
                except ValueError:
                    pass
            
            new_number = str(max_number + 1)
            
            # 添加新行数据
            new_data = {
                'number': new_number,
                'prompt': '新提示词',
                'status': '等待中',
                'image_url': '',
                'error_msg': '',
                'reference_images': []  # 改为支持多张参考图片的列表
            }
            
            self.prompt_table_data.append(new_data)
            self.refresh_prompt_table()
            self.update_prompt_stats()
            
            # 自动选中新添加的行
            new_row = len(self.prompt_table_data) - 1
            self.prompt_table.selectRow(new_row)
            
            # 使用QTimer延迟编辑，确保表格完全更新后再开始编辑
            QTimer.singleShot(100, lambda: self.edit_new_prompt_item(new_row))
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加提示词失败: {str(e)}")
    
    def edit_new_prompt_item(self, row):
        """延迟编辑新添加的提示词项"""
        try:
            if 0 <= row < self.prompt_table.rowCount():
                item = self.prompt_table.item(row, 1)  # 提示词列
                if item:
                    self.prompt_table.editItem(item)
        except Exception as e:
            # 如果编辑失败，不要崩溃，只是记录错误
            print(f"编辑新项失败: {str(e)}")
    
    def delete_selected_prompts(self):
        """删除选中的提示词"""
        selected_rows = set()
        
        # 优先检查复选框选择
        checkbox_selected = False
        for row in range(len(self.prompt_table_data)):
            checkbox = self.prompt_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_rows.add(row)
                checkbox_selected = True
        
        # 如果没有复选框选择，则检查表格行选择
        if not checkbox_selected:
            for item in self.prompt_table.selectedItems():
                selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的提示词（可以通过复选框选择或点击行选择）")
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 个提示词吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 从大到小删除，避免索引变化
            for row in sorted(selected_rows, reverse=True):
                if 0 <= row < len(self.prompt_table_data):
                    del self.prompt_table_data[row]
            
            self.refresh_prompt_table()
            self.update_prompt_stats()
    
    def on_table_cell_changed(self, row, column):
        """表格单元格内容改变"""
        if 0 <= row < len(self.prompt_table_data):
            item = self.prompt_table.item(row, column)
            if item:
                if column == 1:  # 编号列
                    self.prompt_table_data[row]['number'] = item.text().strip()
                elif column == 2:  # 提示词列
                    old_prompt = self.prompt_table_data[row]['prompt']
                    new_prompt = item.text().strip()
                    self.prompt_table_data[row]['prompt'] = new_prompt
                    
                    # 更新提示词编号映射
                    if old_prompt in self.prompt_numbers:
                        number = self.prompt_numbers.pop(old_prompt)
                        self.prompt_numbers[new_prompt] = number
                    
                    # 设置工具提示显示完整内容
                    item.setToolTip(new_prompt)
                    
                    # 调整行高以适应新内容
                    self.prompt_table.resizeRowToContents(row)
                    
                    # 如果文本很长，确保表格能正确显示
                    if len(new_prompt) > 100:  # 长文本时强制刷新
                        self.prompt_table.viewport().update()
    
    def on_table_cell_double_clicked(self, row, column):
        """表格单元格双击"""
        if column == 2:  # 提示词列 - 直接编辑，不弹出对话框
            # 不需要特殊处理，让默认编辑器处理即可
            pass
        elif column == 5:  # 生成状态/图片列（合并后）
            if 0 <= row < len(self.prompt_table_data):
                data = self.prompt_table_data[row]
                if data['status'] == '成功':
                    # 打开图片查看对话框（从本地文件加载）
                    dialog = ImageViewDialog(data['number'], data['prompt'], self.save_path, self)
                    dialog.exec()
    
    def update_batch_optimize_button(self):
        """更新批量优化按钮状态和全选按钮文本"""
        selected_count = 0
        total_count = len(self.prompt_table_data)
        
        for row in range(total_count):
            checkbox = self.prompt_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
        
        # 更新批量优化按钮
        self.batch_optimize_button.setEnabled(selected_count > 0)
        
        # 更新全选按钮文本
        if hasattr(self, 'select_all_button') and self.select_all_button:
            if selected_count == 0:
                self.select_all_button.setText("全选")
            elif selected_count == total_count:
                self.select_all_button.setText("取消全选")
            else:
                self.select_all_button.setText(f"全选({selected_count}/{total_count})")
        
    def toggle_select_all(self):
        """切换全选状态"""
        # 检查当前是否已全选
        all_selected = True
        for row in range(len(self.prompt_table_data)):
            checkbox = self.prompt_table.cellWidget(row, 0)
            if checkbox and not checkbox.isChecked():
                all_selected = False
                break
        
        # 切换状态
        new_state = not all_selected
        for row in range(len(self.prompt_table_data)):
            checkbox = self.prompt_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(new_state)
        
        # 更新按钮状态（会自动更新全选按钮文本）
        self.update_batch_optimize_button()
    
    def batch_optimize_prompts(self):
        """批量优化提示词"""
        if not self.openrouter_api_key:
            QMessageBox.warning(self, "配置错误", "请先在设置中心配置OpenRouter API密钥")
            return
        
        # 收集选中的提示词
        selected_prompts = []
        for row in range(len(self.prompt_table_data)):
            checkbox = self.prompt_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_prompts.append({
                    'row': row,
                    'data': self.prompt_table_data[row]
                })
        
        if not selected_prompts:
            QMessageBox.information(self, "提示", "请至少选择一个提示词进行优化")
            return
        
        # 批量处理
        for prompt_info in selected_prompts:
            self.optimize_prompt(prompt_info['row'], prompt_info['data'])
    
    def generate_single_prompt(self, row):
        """生成单个提示词的图片"""
        # 检查配置
        if not self.get_current_api_key():
            QMessageBox.warning(self, "配置不完整", "请先在设置中心配置API密钥")
            return
        
        if not self.save_path:
            QMessageBox.warning(self, "配置不完整", "请先在设置中心设置保存路径")
            return
        
        if 0 <= row < len(self.prompt_table_data):
            data = self.prompt_table_data[row]
            original_prompt = data['prompt']
            
            # 处理提示词 - 添加风格和比例
            prompt = original_prompt
            
            # 添加风格提示词
            style_content = ""
            if self.custom_style_content.strip():
                style_content = self.custom_style_content.strip()
                if self.current_style and self.current_style in self.style_library:
                    self.style_library[self.current_style]['usage_count'] = self.style_library[self.current_style].get('usage_count', 0) + 1
            elif self.current_style and self.current_style in self.style_library:
                style_content = self.style_library[self.current_style]['content'].strip()
                self.style_library[self.current_style]['usage_count'] = self.style_library[self.current_style].get('usage_count', 0) + 1
            
            ratio = self.image_ratio
            
            # 处理提示词
            if f"图片比例【{ratio}】" not in prompt:
                if style_content and style_content not in prompt:
                    prompt = f"{prompt} {style_content}"
                prompt = f"{prompt} 图片比例【{ratio}】"
            
            # 获取图片数据映射
            image_data_map = self.get_image_data_map()
            
            # 从提示词中提取图片名称
            image_names = self.extract_image_names(prompt)
            
            # 获取对应的图片数据
            image_data_list = []
            for name in image_names:
                if name in image_data_map:
                    image_data_list.append(image_data_map[name])
            
            # 添加拖拽的参考图片（多图支持）
            reference_images = data.get('reference_images', [])
            for img_path in reference_images:
                try:
                    with open(img_path, 'rb') as f:
                        image_data = base64.b64encode(f.read()).decode()
                        image_name = os.path.basename(img_path)
                        image_data_list.append({
                            'name': image_name,
                            'data': image_data,
                            'type': 'drag_reference'
                        })
                except Exception as e:
                    logging.warning(f"无法读取拖拽的参考图片 {img_path}: {str(e)}")
            
            # 获取对应的编号
            number = self.prompt_numbers.get(original_prompt, str(row + 1))
            
            # 更新状态为生成中
            data['status'] = '生成中'
            self.refresh_prompt_table()
            
            # 创建工作线程
            worker = Worker(prompt, self.get_current_api_key(), image_data_list, self.api_platform, self.image_model, self.retry_count, number)
            worker.signals.finished.connect(lambda p, url, num: self.handle_single_success(p, url, num, row, original_prompt))
            worker.signals.error.connect(lambda p, err: self.handle_single_error(p, err, row, original_prompt))
            worker.signals.progress.connect(lambda p, status: self.handle_single_progress(p, status, original_prompt))
            self.threadpool.start(worker)
            
            QMessageBox.information(self, "开始生成", f"已开始生成编号 {number} 的图片")
    
    def handle_single_success(self, prompt, image_url, number, row, original_prompt):
        """处理单个提示词生成成功"""
        try:
            # 更新数据状态
            if 0 <= row < len(self.prompt_table_data):
                self.prompt_table_data[row]['status'] = '成功'
                self.prompt_table_data[row]['image_url'] = image_url
                self.prompt_table_data[row]['error_msg'] = ''
            
            # 存储图片信息
            self.generated_images[prompt] = image_url
            
            # 生成带时间戳前缀的文件名
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{number}.png"
            
            # 将文件名保存到数据中
            if 0 <= row < len(self.prompt_table_data):
                self.prompt_table_data[row]['filename'] = filename
            
            # 自动保存图片
            if self.save_path:
                try:
                    os.makedirs(self.save_path, exist_ok=True)
                    file_path = os.path.join(self.save_path, filename)
                    
                    response = requests.get(image_url)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                        
                except Exception as e:
                    error_msg = f"保存图片失败: {str(e)}"
                    logging.error(error_msg)
            
            # 刷新显示
            self.refresh_prompt_table()
            
            # 播放完成提示音
            try:
                if hasattr(winsound, 'SND_ASYNC'):
                    winsound.MessageBeep()
            except:
                pass
                
            QMessageBox.information(self, "生成完成", f"编号 {number} 的图片生成成功！")
            
        except Exception as e:
            logging.error(f"处理单个生成成功时出错: {str(e)}")
            QMessageBox.critical(self, "处理错误", f"图片生成成功，但保存时出错: {str(e)}")
    
    def handle_single_error(self, prompt, error_msg, row, original_prompt):
        """处理单个提示词生成失败"""
        try:
            # 更新数据状态
            if 0 <= row < len(self.prompt_table_data):
                self.prompt_table_data[row]['status'] = '失败'
            
            # 刷新显示
            self.refresh_prompt_table()
            
            QMessageBox.critical(self, "生成失败", f"图片生成失败:\n{error_msg}")
            
        except Exception as e:
            logging.error(f"处理单个生成失败时出错: {str(e)}")
    
    def handle_single_progress(self, prompt, status, original_prompt):
        """处理单个提示词生成进度"""
        try:
            # 找到对应的行并更新状态
            for i, data in enumerate(self.prompt_table_data):
                if data['prompt'] == original_prompt:
                    data['status'] = status
                    break
            
            # 刷新显示
            self.refresh_prompt_table()
            
        except Exception as e:
            logging.error(f"处理单个生成进度时出错: {str(e)}")

    def optimize_single_prompt(self, row):
        """优化单个提示词"""
        if not self.openrouter_api_key:
            QMessageBox.warning(self, "配置错误", "请先在设置中心配置OpenRouter API密钥")
            return
        
        if 0 <= row < len(self.prompt_table_data):
            data = self.prompt_table_data[row]
            self.optimize_prompt(row, data)
    
    def optimize_prompt(self, row, data):
        """调用OpenRouter API优化提示词"""
        try:
            # 准备API请求
            headers = {
                'Authorization': f'Bearer {self.openrouter_api_key}',
                'Content-Type': 'application/json'
            }
            
            # 构建优化请求文本
            prompt_text = f"{self.meta_prompt}\n\n待优化提示词：{data['prompt']}"
            
            request_data = {
                'model': self.ai_model,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_text
                    }
                ],
                'temperature': 0.7
            }
            
            # 发送请求
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers=headers,
                json=request_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                optimized_text = result['choices'][0]['message']['content']
                
                # 显示优化结果对话框
                self.show_optimization_result(data['prompt'], optimized_text, row)
            else:
                QMessageBox.warning(self, "API错误", f"请求失败：{response.status_code}\n{response.text}")
                
        except Exception as e:
            QMessageBox.critical(self, "优化错误", f"优化过程中出现错误：{str(e)}")
    
    def show_optimization_result(self, original_prompt, optimized_prompt, row):
        """显示优化结果对话框"""
        dialog = OptimizationResultDialog(original_prompt, optimized_prompt, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 用户选择应用优化结果 - 获取用户可能编辑过的文本
            final_optimized_prompt = dialog.get_final_optimized_text()
            self.prompt_table_data[row]['prompt'] = final_optimized_prompt
            
            # 保存到历史记录
            history_item = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'original': original_prompt,
                'optimized': final_optimized_prompt,
                'model': self.ai_model,
                'meta_prompt': self.meta_prompt
            }
            self.optimization_history.append(history_item)
            
            # 刷新表格显示
            self.refresh_prompt_table()
            self.save_config()
    
    def get_image_data_map(self):
        """获取所有图片数据映射"""
        image_data_map = {}
        for cat, links in self.category_links.items():
            for link in links:
                if link['name']:
                    image_data_map[link['name']] = link
        return image_data_map
    
    def extract_image_names(self, prompt):
        """从提示词中提取图片名称"""
        image_names = []
        all_names = []
        
        # 收集所有图片名称
        for cat_links in self.category_links.values():
            for link in cat_links:
                name = link['name'].strip()
                if name:
                    all_names.append(name)
        
        # 按长度排序，优先匹配更长的名称
        all_names.sort(key=len, reverse=True)
        
        # 找到所有能匹配的图片名称
        for name in all_names:
            if name in prompt:
                image_names.append(name)
        
        return image_names
    
    def start_generation(self):
        """开始生成图片"""
        # 检查配置
        if not self.get_current_api_key():
            QMessageBox.warning(self, "配置不完整", "请先在设置中心配置API密钥")
            return
        
        if not self.save_path:
            QMessageBox.warning(self, "配置不完整", "请先在设置中心设置保存路径")
            return
        
        # 检查是否有提示词
        if not self.prompt_table_data:
            QMessageBox.warning(self, "提示", "请先添加提示词或导入CSV文件")
            return
        
        self.save_config()
        
        # 获取提示词 - 只处理等待中的提示词
        prompts = []
        original_prompts = []
        
        # 只获取状态为'等待中'的提示词
        for data in self.prompt_table_data:
            if data.get('status', '等待中') == '等待中':
                prompts.append(data['prompt'])
                original_prompts.append(data['prompt'])
        
        # 检查是否有需要生成的提示词
        if not prompts:
            QMessageBox.information(self, "提示", "没有需要生成的新提示词！\n\n所有提示词都已生成完成或正在生成中。")
            return
            
        # 刷新表格显示
        self.refresh_prompt_table()
        
        # 添加风格提示词和图片比例
        style_content = ""
        if self.custom_style_content.strip():
            style_content = self.custom_style_content.strip()
            if self.current_style and self.current_style in self.style_library:
                self.style_library[self.current_style]['usage_count'] = self.style_library[self.current_style].get('usage_count', 0) + 1
        elif self.current_style and self.current_style in self.style_library:
            style_content = self.style_library[self.current_style]['content'].strip()
            self.style_library[self.current_style]['usage_count'] = self.style_library[self.current_style].get('usage_count', 0) + 1
        
        ratio = self.image_ratio
        
        # 处理每个提示词
        processed_prompts = []
        for p in prompts:
            if f"图片比例【{ratio}】" not in p:
                if style_content and style_content not in p:
                    p = f"{p} {style_content}"
                p = f"{p} 图片比例【{ratio}】"
            processed_prompts.append(p)
        
        prompts = processed_prompts
        
        # 设置计数器（保持兼容性）
        self.total_images = len(prompts)
        self.completed_images = 0
        
        # 显示整体进度
        self.overall_progress_bar.setVisible(True)
        self.overall_progress_label.setText(f"开始生成 {len(prompts)} 张新图片...")
        
        # 更新进度显示
        self.update_generation_progress()
        
        # 更新按钮状态（但不禁用，允许继续添加新提示词）
        self.generate_button.setText("继续生成新增")
        
        # 获取图片数据映射
        image_data_map = self.get_image_data_map()
        
        # 为每个提示词创建工作线程
        for i, prompt in enumerate(prompts):
            # 从提示词中提取图片名称
            image_names = self.extract_image_names(prompt)
            
            # 获取对应的图片数据
            image_data_list = []
            for name in image_names:
                if name in image_data_map:
                    image_data_list.append(image_data_map[name])
            
            # 获取对应的编号
            original_prompt = original_prompts[i]
            number = self.prompt_numbers.get(original_prompt, str(i + 1))
            
            worker = Worker(prompt, self.get_current_api_key(), image_data_list, self.api_platform, self.image_model, self.retry_count, number)
            worker.signals.finished.connect(lambda p, url, num, idx=i, orig=original_prompt: self.handle_success(p, url, num, idx, orig))
            worker.signals.error.connect(lambda p, err, idx=i, orig=original_prompt: self.handle_error(p, err, idx, orig))
            worker.signals.progress.connect(lambda p, status, orig=original_prompt: self.handle_progress(p, status, orig))
            self.threadpool.start(worker)
    
    def start_regenerate_all(self):
        """重新生成全部提示词"""
        # 确认操作
        reply = QMessageBox.question(
            self, 
            "确认重新生成", 
            "确定要重新生成全部提示词吗？\n\n这将重置所有状态并重新开始生成。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 检查配置
        if not self.get_current_api_key():
            QMessageBox.warning(self, "配置不完整", "请先在设置中心配置API密钥")
            return
        
        if not self.save_path:
            QMessageBox.warning(self, "配置不完整", "请先在设置中心设置保存路径")
            return
        
        # 检查是否有提示词
        if not self.prompt_table_data:
            QMessageBox.warning(self, "提示", "请先添加提示词或导入CSV文件")
            return
        
        self.save_config()
        
        # 获取所有提示词并重置状态
        prompts = []
        original_prompts = []
        
        # 重置所有状态
        for data in self.prompt_table_data:
            data['status'] = '等待中'
            data['image_url'] = ''
            data['error_msg'] = ''
            prompts.append(data['prompt'])
            original_prompts.append(data['prompt'])
            
        # 刷新表格显示
        self.refresh_prompt_table()
        
        # 添加风格提示词和图片比例
        style_content = ""
        if self.custom_style_content.strip():
            style_content = self.custom_style_content.strip()
            if self.current_style and self.current_style in self.style_library:
                self.style_library[self.current_style]['usage_count'] = self.style_library[self.current_style].get('usage_count', 0) + 1
        elif self.current_style and self.current_style in self.style_library:
            style_content = self.style_library[self.current_style]['content'].strip()
            self.style_library[self.current_style]['usage_count'] = self.style_library[self.current_style].get('usage_count', 0) + 1
        
        ratio = self.image_ratio
        
        # 处理每个提示词
        processed_prompts = []
        for p in prompts:
            if f"图片比例【{ratio}】" not in p:
                if style_content and style_content not in p:
                    p = f"{p} {style_content}"
                p = f"{p} 图片比例【{ratio}】"
            processed_prompts.append(p)
        
        prompts = processed_prompts
        
        # 设置计数器（保持兼容性）
        self.total_images = len(prompts)
        self.completed_images = 0
        
        # 显示整体进度
        self.overall_progress_bar.setVisible(True)
        self.overall_progress_label.setText(f"开始重新生成 {len(prompts)} 张图片...")
        
        # 更新进度显示
        self.update_generation_progress()
        
        # 重新生成全部时禁用按钮（避免冲突）
        self.generate_button.setEnabled(False)
        self.generate_button.setText("重新生成中...")
        self.regenerate_all_button.setEnabled(False)
        self.regenerate_all_button.setText("重新生成中...")
        
        # 获取图片数据映射
        image_data_map = self.get_image_data_map()
        
        # 为每个提示词创建工作线程
        for i, prompt in enumerate(prompts):
            # 从提示词中提取图片名称
            image_names = self.extract_image_names(prompt)
            
            # 获取对应的图片数据
            image_data_list = []
            for name in image_names:
                if name in image_data_map:
                    image_data_list.append(image_data_map[name])
            
            # 获取对应的编号
            original_prompt = original_prompts[i]
            number = self.prompt_numbers.get(original_prompt, str(i + 1))
            
            worker = Worker(prompt, self.get_current_api_key(), image_data_list, self.api_platform, self.image_model, self.retry_count, number)
            worker.signals.finished.connect(lambda p, url, num, idx=i, orig=original_prompt: self.handle_success(p, url, num, idx, orig))
            worker.signals.error.connect(lambda p, err, idx=i, orig=original_prompt: self.handle_error(p, err, idx, orig))
            worker.signals.progress.connect(lambda p, status, orig=original_prompt: self.handle_progress(p, status, orig))
            self.threadpool.start(worker)
    
    def handle_progress(self, prompt, status, original_prompt):
        """处理进度更新"""
        # 找到对应的数据行
        for data in self.prompt_table_data:
            if data['prompt'] == original_prompt:
                if "重试" in status:
                    data['status'] = status
                else:
                    data['status'] = '生成中'
                break
        
        # 刷新表格显示
        self.refresh_prompt_table()
    
    def handle_success(self, prompt, image_url, number, index, original_prompt):
        """处理成功"""
        # 找到对应的数据行并更新
        actual_number = number  # 默认使用传入的编号
        found = False
        for data in self.prompt_table_data:
            if data['prompt'] == original_prompt:
                data['status'] = '成功'
                data['image_url'] = image_url
                data['error_msg'] = ''
                actual_number = data['number']  # 使用表格中的编号
                found = True
                break
        
        # 存储图片信息
        self.generated_images[prompt] = image_url
        
        # 生成带时间戳前缀的文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{actual_number}.png"
        
        # 将文件名保存到数据中
        for data in self.prompt_table_data:
            if data['prompt'] == original_prompt:
                data['filename'] = filename
                break
        
        # 自动保存图片
        if self.save_path:
            try:
                os.makedirs(self.save_path, exist_ok=True)
                file_path = os.path.join(self.save_path, filename)
                
                response = requests.get(image_url)
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                    
            except Exception as e:
                error_msg = f"保存图片失败: {str(e)}"
                logging.error(error_msg)
        
        # 刷新表格显示
        self.refresh_prompt_table()
        
        # 动态计算当前任务状态
        self.update_generation_progress()
        
        # 检查是否当前批次全部完成
        self.check_generation_completion()
    
    def handle_error(self, prompt, error, index, original_prompt):
        """处理错误"""
        # 找到对应的数据行并更新
        for data in self.prompt_table_data:
            if data['prompt'] == original_prompt:
                data['status'] = '失败'
                data['image_url'] = ''
                data['error_msg'] = error
                break
        
        # 刷新表格显示
        self.refresh_prompt_table()
        
        # 记录错误
        logging.error(f"生成图片 {index+1} 失败:")
        logging.error(f"提示词: {prompt}")
        logging.error(f"错误信息: {error}")
        
        # 动态计算当前任务状态
        self.update_generation_progress()
        
        # 检查是否当前批次全部完成
        self.check_generation_completion()
    
    def update_generation_progress(self):
        """动态更新生成进度"""
        # 统计各种状态的任务数量
        waiting_count = len([data for data in self.prompt_table_data if data.get('status', '等待中') == '等待中'])
        generating_count = len([data for data in self.prompt_table_data if data.get('status', '') == '生成中' or '重试' in data.get('status', '')])
        success_count = len([data for data in self.prompt_table_data if data.get('status', '') == '成功'])
        failed_count = len([data for data in self.prompt_table_data if data.get('status', '') == '失败'])
        
        total_tasks = len(self.prompt_table_data)
        completed_tasks = success_count + failed_count
        
        # 更新进度条
        if total_tasks > 0:
            self.overall_progress_bar.setMaximum(total_tasks)
            self.overall_progress_bar.setValue(completed_tasks)
            
            # 更新进度标签
            if generating_count > 0:
                self.overall_progress_label.setText(f"进行中: 等待{waiting_count}个 | 生成中{generating_count}个 | 已完成{success_count}个 | 失败{failed_count}个")
            else:
                self.overall_progress_label.setText(f"已处理 {completed_tasks}/{total_tasks} 个任务 | 成功{success_count}个 | 失败{failed_count}个")
    
    def check_generation_completion(self):
        """检查生成是否完成"""
        # 检查是否还有正在生成或等待中的任务
        active_tasks = [data for data in self.prompt_table_data 
                       if data.get('status', '等待中') in ['等待中', '生成中'] or '重试' in data.get('status', '')]
        
        # 如果没有活跃任务，说明当前批次已完成
        if not active_tasks:
            # 只有在重新生成全部模式下才完全恢复按钮状态
            if not self.generate_button.isEnabled():  # 说明是重新生成全部模式
                self.generation_finished()
    
    def generation_finished(self):
        """生成完成"""
        self.generate_button.setEnabled(True)
        self.generate_button.setText("智能生成(仅新增)")
        self.regenerate_all_button.setEnabled(True)
        self.regenerate_all_button.setText("重新生成全部")
        
        # 统计结果
        success_count = len([data for data in self.prompt_table_data if data['status'] == '成功'])
        failed_count = self.total_images - success_count
        
        # 更新状态显示
        self.overall_progress_label.setText(f"🎉 生成完成！成功: {success_count} 张，失败: {failed_count} 张")
        
        # 播放完成提示音
        self.play_completion_sound()
    
    def check_default_config(self):
        """检查并创建默认配置文件"""
        config_path = APP_PATH / 'config.json'
        if not config_path.exists():
            # 异步创建，避免阻塞启动
            QTimer.singleShot(300, lambda: self.create_default_config_file(config_path))
    
    def create_default_config_file(self, config_path):
        """异步创建默认配置文件"""
        if config_path.exists():  # 双重检查
            return
        try:
            default_config = {
                'api_key': '',
                'api_platform': '云雾',
                'thread_count': 5,
                'retry_count': 3,
                'save_path': '',
                'image_ratio': '3:2',
                'style_library': {
                    '超写实风格': {
                        'name': '超写实风格',
                        'content': '极致的超写实主义照片风格，画面呈现出顶级数码单反相机（如佳能EOS R5）搭配高质量定焦镜头（如85mm f/1.2）的拍摄效果。明亮、均匀，光影过渡微妙且真实，无明显阴影。绝对真实的全彩照片，无任何色彩滤镜。色彩如同在D65标准光源环境下拍摄，白平衡极其精准，所见即所得。色彩干净通透，类似于现代商业广告摄影风格。严禁任何形式的棕褐色调、复古滤镜或暖黄色偏色。画面高度细腻，细节极其丰富，达到8K分辨率的视觉效果。追求极致的清晰度和纹理表现，所有物体的材质质感都应逼真呈现，无噪点，无失真。',
                        'category': '摄影风格',
                        'created_time': '2024-01-01 12:00:00',
                        'usage_count': 0
                    },
                    '动漫风格': {
                        'name': '动漫风格',
                        'content': '二次元动漫风格，色彩鲜艳饱满，线条清晰，具有典型的日式动漫美学特征。人物造型精致，表情生动，背景细腻。',
                        'category': '插画风格',
                        'created_time': '2024-01-01 12:01:00',
                        'usage_count': 0
                    },
                    '油画风格': {
                        'name': '油画风格',
                        'content': '经典油画艺术风格，笔触丰富，色彩层次分明，具有厚重的质感和艺术气息。光影效果自然，构图典雅。',
                        'category': '艺术风格',
                        'created_time': '2024-01-01 12:02:00',
                        'usage_count': 0
                    }
                },
                'current_style': '',
                'custom_style_content': '',
                'window_geometry': {
                    'width': 1200,
                    'height': 800,
                    'x': 100,
                    'y': 100
                },
                'category_links': {}
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # 静默失败，不影响程序运行
    
    def load_config(self):
        """加载配置"""
        try:
            config_path = APP_PATH / 'config.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.api_key = config.get('api_key', '')
                self.api_platform = config.get('api_platform', '云雾')
                self.image_model = config.get('image_model', 'sora')  # 加载生图模型配置
                # 加载分离的API密钥
                self.sora_api_key = config.get('sora_api_key', '')
                self.nano_api_key = config.get('nano_api_key', '')
                self.thread_count = config.get('thread_count', 5)
                self.retry_count = config.get('retry_count', 3)
                self.save_path = config.get('save_path', '')
                self.image_ratio = config.get('image_ratio', '3:2')
                
                # 加载风格库
                self.style_library = config.get('style_library', {})
                self.current_style = config.get('current_style', '')
                self.custom_style_content = config.get('custom_style_content', '')
                
                # 加载图片分类链接
                self.category_links = config.get('category_links', {})
                
                # 加载OpenRouter AI优化配置
                self.openrouter_api_key = config.get('openrouter_api_key', '')
                self.ai_model = config.get('ai_model', 'qwen/qwq-32b')
                self.meta_prompt = config.get('meta_prompt', '')
                self.meta_prompt_template = config.get('meta_prompt_template', 'template1')
                self.optimization_history = config.get('optimization_history', [])
                
                # 恢复窗口大小和位置
                window_geometry = config.get('window_geometry', {})
                if window_geometry:
                    width = window_geometry.get('width', 1200)
                    height = window_geometry.get('height', 800)
                    x = window_geometry.get('x', 100)
                    y = window_geometry.get('y', 100)
                    
                    self.resize(width, height)
                    self.move(x, y)
                
                # 异步刷新界面显示（避免阻塞）
                QTimer.singleShot(50, self.refresh_ui_after_settings)
                
                # 刷新提示词表格中的按钮状态
                QTimer.singleShot(100, self.refresh_prompt_table)

        except FileNotFoundError:
            # 即使没有配置文件，也要异步刷新UI
            QTimer.singleShot(50, self.refresh_ui_after_settings)
            QTimer.singleShot(100, self.refresh_prompt_table)
        except Exception as e:
            # 即使配置加载失败，也要异步刷新UI
            QTimer.singleShot(50, self.refresh_ui_after_settings)
            QTimer.singleShot(100, self.refresh_prompt_table)
    
    def save_config(self):
        """保存配置"""
        if not self._init_done:
            return
        try:
            config = {
                'api_key': self.api_key,
                'api_platform': self.api_platform,
                'image_model': self.image_model,  # 保存生图模型配置
                # 分离的API密钥
                'sora_api_key': getattr(self, 'sora_api_key', ''),
                'nano_api_key': getattr(self, 'nano_api_key', ''),
                'thread_count': self.thread_count,
                'retry_count': self.retry_count,
                'save_path': self.save_path,
                'image_ratio': self.image_ratio,
                'style_library': self.style_library,
                'current_style': self.current_style,
                'custom_style_content': self.custom_style_content,
                'window_geometry': {
                    'width': self.width(),
                    'height': self.height(),
                    'x': self.x(),
                    'y': self.y()
                },
                'category_links': self.category_links,
                # OpenRouter AI优化配置
                'openrouter_api_key': self.openrouter_api_key,
                'ai_model': self.ai_model,
                'meta_prompt': self.meta_prompt,
                'meta_prompt_template': self.meta_prompt_template,
                'optimization_history': self.optimization_history
            }
            config_path = APP_PATH / 'config.json'
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            pass
    
    def play_completion_sound(self):
        """播放任务完成提示音"""
        try:
            if winsound:
                # Windows系统：播放系统完成提示音
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
            elif subprocess:
                # 跨平台方案
                if sys.platform.startswith('darwin'):  # macOS
                    subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], check=False)
                elif sys.platform.startswith('linux'):  # Linux
                    subprocess.run(['aplay', '/usr/share/sounds/alsa/Front_Right.wav'], check=False)
        except Exception as e:
            # 如果播放声音失败，忽略错误
            pass
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.save_config()
        event.accept()

def main():
    """主函数，包含完整的错误处理"""
    try:
        # 设置环境变量，解决各种兼容性问题
        os.environ['PYTHONHASHSEED'] = '0'
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
        
        # 创建应用程序实例
        app = QApplication(sys.argv)
        
        # 设置应用程序属性
        app.setApplicationName("深海圈生图")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("深海圈工作室")
        
        # 设置异常处理
        sys.excepthook = handle_exception
        
        try:
            # 创建主窗口
            window = MainWindow()
            window.show()
            
            # 运行应用程序
            return app.exec()
            
        except Exception as e:
            # 主窗口创建失败时的处理
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("启动错误")
            error_dialog.setText("程序初始化失败")
            error_dialog.setDetailedText(f"错误详情:\n{str(e)}\n\n可能的解决方案:\n1. 重启程序\n2. 检查配置文件\n3. 重新安装依赖")
            error_dialog.exec()
            return 1
        
    except ImportError as e:
        print(f"❌ 模块导入错误: {e}")
        print("\n请运行以下命令安装依赖:")
        print("pip install PyQt6 requests pandas")
        print("\n或者双击运行 '简单启动.bat'")
        input("\n按回车键退出...")
        return 1
        
    except Exception as e:
        print(f"❌ 应用程序启动失败: {e}")
        print(f"\nPython版本: {sys.version}")
        print("\n可能的解决方案:")
        print("1. 确保Python版本3.8+")
        print("2. 重新安装依赖包")
        print("3. 以管理员权限运行")
        input("\n按回车键退出...")
        return 1

def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理器"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"程序发生未处理的异常:\n{error_msg}")
    
    # 保存详细错误信息到文件
    try:
        with open("crash_log.txt", "w", encoding="utf-8") as f:
            f.write(f"程序崩溃日志 - {datetime.datetime.now()}\n")
            f.write(f"Python版本: {sys.version}\n")
            f.write(f"工作目录: {os.getcwd()}\n\n")
            f.write("异常详情:\n")
            f.write(error_msg)
            f.write("\n" + "="*50 + "\n")
    except:
        pass
    
    # 尝试显示错误对话框
    try:
        from PyQt6.QtWidgets import QMessageBox, QApplication
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("程序错误")
            msg.setText("程序遇到了一个错误")
            msg.setDetailedText(f"{error_msg}\n\n详细信息已保存到 crash_log.txt")
            msg.exec()
    except:
        pass


class ReferenceImageDialog(QDialog):
    """参考图片查看对话框"""
    
    def __init__(self, image_path, prompt, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.prompt = prompt
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("参考图片")
        self.setModal(True)
        self.resize(600, 700)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("🖼️ 参考图片")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # 图片显示
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setMinimumHeight(400)
        image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
        """)
        
        # 加载图片
        try:
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                # 缩放图片以适应显示区域
                scaled_pixmap = pixmap.scaled(550, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(scaled_pixmap)
            else:
                image_label.setText("无法加载图片")
        except Exception as e:
            image_label.setText(f"加载错误: {str(e)}")
            
        layout.addWidget(image_label)
        
        # 图片信息
        info_layout = QVBoxLayout()
        
        # 文件名
        filename_label = QLabel(f"文件名: {os.path.basename(self.image_path)}")
        filename_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        info_layout.addWidget(filename_label)
        
        # 文件路径
        path_label = QLabel(f"路径: {self.image_path}")
        path_label.setStyleSheet("font-size: 12px; color: #666;")
        path_label.setWordWrap(True)
        info_layout.addWidget(path_label)
        
        # 当前提示词
        prompt_label = QLabel("当前提示词:")
        prompt_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        info_layout.addWidget(prompt_label)
        
        prompt_text = QLabel(self.prompt)
        prompt_text.setStyleSheet("font-size: 12px; padding: 8px; background-color: #f8f9fa; border-radius: 4px;")
        prompt_text.setWordWrap(True)
        info_layout.addWidget(prompt_text)
        
        layout.addLayout(info_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        open_button = QPushButton("打开文件夹")
        open_button.clicked.connect(self.open_file_location)
        button_layout.addWidget(open_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
    def open_file_location(self):
        """打开文件所在文件夹"""
        try:
            if sys.platform == "win32":
                os.startfile(os.path.dirname(self.image_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", os.path.dirname(self.image_path)])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(self.image_path)])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {str(e)}")

class OptimizationResultDialog(QDialog):
    """优化结果对话框"""
    
    def __init__(self, original_prompt, optimized_prompt, parent=None):
        super().__init__(parent)
        self.original_prompt = original_prompt
        self.optimized_prompt = optimized_prompt
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("AI优化结果")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("提示词优化结果")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # 创建分割窗口
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # 原始提示词区域
        original_group = QGroupBox("原始提示词")
        original_layout = QVBoxLayout(original_group)
        self.original_text = QTextEdit()
        self.original_text.setPlainText(self.original_prompt)
        self.original_text.setReadOnly(True)
        original_layout.addWidget(self.original_text)
        splitter.addWidget(original_group)
        
        # 优化后提示词区域
        optimized_group = QGroupBox("优化后提示词")
        optimized_layout = QVBoxLayout(optimized_group)
        self.optimized_text = QTextEdit()
        self.optimized_text.setPlainText(self.optimized_prompt)
        optimized_layout.addWidget(self.optimized_text)
        splitter.addWidget(optimized_group)
        
        # 设置分割比例
        splitter.setSizes([200, 300])
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("应用优化结果")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.apply_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        # 复制按钮
        copy_btn = QPushButton("复制优化结果")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        copy_btn.clicked.connect(self.copy_optimized_text)
        
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.apply_btn)
        
        layout.addLayout(button_layout)
    
    def copy_optimized_text(self):
        """复制优化结果到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.optimized_text.toPlainText())
        QMessageBox.information(self, "提示", "优化结果已复制到剪贴板")
    
    def get_final_optimized_text(self):
        """获取最终的优化文本（可能被用户编辑过）"""
        return self.optimized_text.toPlainText()


class ReferenceImagesManagerDialog(QDialog):
    """参考图片管理对话框 - 带缩略图预览"""
    
    def __init__(self, images, parent=None):
        super().__init__(parent)
        self.images = list(images)  # 复制一份，避免直接修改原列表
        self.setWindowTitle("管理参考图片")
        self.setFixedSize(700, 500)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel(f"共 {len(self.images)} 张参考图片")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # 创建分割布局
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧：图片列表（带缩略图）
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        list_label = QLabel("图片列表：")
        list_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        left_layout.addWidget(list_label)
        
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setIconSize(QSize(60, 60))  # 设置图标大小
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.list_widget)
        
        main_splitter.addWidget(left_widget)
        
        # 右侧：预览区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        preview_label = QLabel("图片预览：")
        preview_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        right_layout.addWidget(preview_label)
        
        # 预览图片标签
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(200, 200)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f8f9fa;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setText("选择图片查看预览")
        right_layout.addWidget(self.preview_label)
        
        # 图片信息标签
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #666; font-size: 11px; margin-top: 5px;")
        right_layout.addWidget(self.info_label)
        
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([350, 350])  # 设置左右比例
        
        # 填充图片列表
        self.refresh_list()
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("添加图片")
        add_button.clicked.connect(self.add_images)
        button_layout.addWidget(add_button)
        
        remove_button = QPushButton("删除选中")
        remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(remove_button)
        
        clear_button = QPushButton("清空全部")
        clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_button)
        
        button_layout.addStretch()
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def refresh_list(self):
        """刷新图片列表显示（带缩略图）"""
        self.list_widget.clear()
        for i, img_path in enumerate(self.images):
            img_name = os.path.basename(img_path)
            item = QListWidgetItem(f"{i+1}. {img_name}")
            item.setToolTip(img_path)
            item.setData(Qt.ItemDataRole.UserRole, img_path)
            
            # 加载缩略图
            try:
                if os.path.exists(img_path):
                    pixmap = QPixmap(img_path)
                    if not pixmap.isNull():
                        # 创建60x60的缩略图
                        scaled_pixmap = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        item.setIcon(QIcon(scaled_pixmap))
            except Exception as e:
                print(f"加载缩略图失败: {e}")
            
            self.list_widget.addItem(item)
    
    def on_selection_changed(self, current, previous):
        """选择项改变时更新预览"""
        if current:
            img_path = current.data(Qt.ItemDataRole.UserRole)
            self.show_preview(img_path)
        else:
            self.preview_label.setText("选择图片查看预览")
            self.info_label.setText("")
    
    def show_preview(self, img_path):
        """显示图片预览"""
        try:
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # 缩放图片适应预览区域
                    preview_size = self.preview_label.size()
                    scaled_pixmap = pixmap.scaled(
                        preview_size.width() - 20, 
                        preview_size.height() - 20, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
                    
                    # 显示图片信息
                    img_name = os.path.basename(img_path)
                    file_size = os.path.getsize(img_path)
                    size_mb = file_size / (1024 * 1024)
                    self.info_label.setText(f"文件名: {img_name}\n大小: {size_mb:.2f} MB\n尺寸: {pixmap.width()}x{pixmap.height()}")
                else:
                    self.preview_label.setText("无法加载图片")
                    self.info_label.setText("图片格式不支持")
            else:
                self.preview_label.setText("文件不存在")
                self.info_label.setText("图片文件已被移动或删除")
        except Exception as e:
            self.preview_label.setText("预览失败")
            self.info_label.setText(f"错误: {str(e)}")
    
    def add_images(self):
        """添加更多图片"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择参考图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*.*)"
        )
        
        if file_paths:
            self.images.extend(file_paths)
            self.refresh_list()
    
    def remove_selected(self):
        """删除选中的图片"""
        current_row = self.list_widget.currentRow()
        if 0 <= current_row < len(self.images):
            self.images.pop(current_row)
            self.refresh_list()
    
    def clear_all(self):
        """清空所有图片"""
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确定要删除所有参考图片吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.images.clear()
            self.refresh_list()
    
    def get_images(self):
        """获取当前的图片列表"""
        return self.images


if __name__ == '__main__':
    import traceback
    sys.exit(main()) 