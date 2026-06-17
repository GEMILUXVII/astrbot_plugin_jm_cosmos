"""
JMComic 打包模块 - 支持加密ZIP和PDF
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

try:
    import pyzipper

    PYZIPPER_AVAILABLE = True
except ImportError:
    PYZIPPER_AVAILABLE = False

try:
    import fitz  # pymupdf

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 长图打包参数
_LONG_IMG_WIDTH = 1200  # 统一宽度，所有图片缩放到此宽度后纵向拼接
_LONG_IMG_MAX_STRIP_HEIGHT = 12000  # 单段长图最大高度，超出则分段
_LONG_IMG_MAX_PER_STRIP = 30  # 单段长图最多包含的图片数
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@dataclass
class PackResult:
    """打包结果"""

    success: bool
    output_path: Path | None
    format: str
    encrypted: bool
    error_message: str | None = None


class JMPacker:
    """JMComic 打包器"""

    def __init__(self, pack_format: str = "zip", password: str = ""):
        """
        初始化打包器

        Args:
            pack_format: 打包格式 (zip/pdf/none)
            password: 加密密码，为空则不加密
        """
        self.pack_format = pack_format.lower()
        self.password = password

    def pack(
        self, source_dir: Path, output_name: str, output_dir: Path | None = None
    ) -> PackResult:
        """
        打包目录

        Args:
            source_dir: 源目录
            output_name: 输出文件名（不含扩展名）
            output_dir: 输出目录，默认为源目录的父目录

        Returns:
            PackResult 打包结果
        """
        if not source_dir.exists():
            return PackResult(
                success=False,
                output_path=None,
                format=self.pack_format,
                encrypted=bool(self.password),
                error_message=f"源目录不存在: {source_dir}",
            )

        if output_dir is None:
            output_dir = source_dir.parent

        output_dir.mkdir(parents=True, exist_ok=True)

        if self.pack_format == "zip":
            return self._pack_zip(source_dir, output_name, output_dir)
        elif self.pack_format == "pdf":
            return self._pack_pdf(source_dir, output_name, output_dir)
        elif self.pack_format == "long_img":
            return self._pack_long_img(source_dir, output_name, output_dir)
        elif self.pack_format == "none":
            return PackResult(
                success=True, output_path=source_dir, format="none", encrypted=False
            )
        else:
            return PackResult(
                success=False,
                output_path=None,
                format=self.pack_format,
                encrypted=False,
                error_message=f"不支持的打包格式: {self.pack_format}",
            )

    def _pack_zip(
        self, source_dir: Path, output_name: str, output_dir: Path
    ) -> PackResult:
        """打包为ZIP"""
        output_path = output_dir / f"{output_name}.zip"

        # 请求了加密但缺少 pyzipper：失败关闭，不静默产出未加密压缩包
        if self.password and not PYZIPPER_AVAILABLE:
            return PackResult(
                success=False,
                output_path=None,
                format="zip",
                encrypted=False,
                error_message=(
                    "已设置打包密码但未安装 pyzipper，无法生成加密 ZIP；"
                    "请安装 pyzipper 或清空打包密码"
                ),
            )

        try:
            if self.password:
                # 使用pyzipper创建加密ZIP
                with pyzipper.AESZipFile(
                    output_path,
                    "w",
                    compression=pyzipper.ZIP_DEFLATED,
                    encryption=pyzipper.WZ_AES,
                ) as zf:
                    zf.setpassword(self.password.encode("utf-8"))
                    for root, dirs, files in os.walk(source_dir):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(source_dir)
                            zf.write(file_path, arcname)
            else:
                # 使用标准库创建普通ZIP
                import zipfile

                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(source_dir):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(source_dir)
                            zf.write(file_path, arcname)

            return PackResult(
                success=True,
                output_path=output_path,
                format="zip",
                encrypted=bool(self.password),
            )

        except Exception as e:
            return PackResult(
                success=False,
                output_path=None,
                format="zip",
                encrypted=False,
                error_message=str(e),
            )

    def _pack_pdf(
        self, source_dir: Path, output_name: str, output_dir: Path
    ) -> PackResult:
        """打包为PDF"""
        if not PYMUPDF_AVAILABLE:
            return PackResult(
                success=False,
                output_path=None,
                format="pdf",
                encrypted=False,
                error_message="pymupdf 库未安装，无法创建PDF",
            )

        output_path = output_dir / f"{output_name}.pdf"

        try:
            # 收集所有图片文件
            image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
            image_files: list[Path] = []

            for root, dirs, files in os.walk(source_dir):
                for file in sorted(files):  # 按文件名排序
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in image_extensions:
                        image_files.append(file_path)

            if not image_files:
                return PackResult(
                    success=False,
                    output_path=None,
                    format="pdf",
                    encrypted=False,
                    error_message="未找到图片文件",
                )

            # 创建PDF
            doc = fitz.open()

            for img_path in image_files:
                try:
                    # 打开图片
                    img = fitz.open(img_path)
                    # 将图片转换为PDF页面
                    pdfbytes = img.convert_to_pdf()
                    img.close()

                    # 插入页面
                    imgpdf = fitz.open("pdf", pdfbytes)
                    doc.insert_pdf(imgpdf)
                    imgpdf.close()
                except Exception:
                    continue  # 跳过无法处理的图片

            if doc.page_count == 0:
                doc.close()
                return PackResult(
                    success=False,
                    output_path=None,
                    format="pdf",
                    encrypted=False,
                    error_message="无法创建PDF页面",
                )

            # 保存PDF（可选加密）
            if self.password:
                doc.save(
                    output_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    owner_pw=self.password,
                    user_pw=self.password,
                    permissions=fitz.PDF_PERM_ACCESSIBILITY,
                )
            else:
                doc.save(output_path)

            doc.close()

            return PackResult(
                success=True,
                output_path=output_path,
                format="pdf",
                encrypted=bool(self.password),
            )

        except Exception as e:
            return PackResult(
                success=False,
                output_path=None,
                format="pdf",
                encrypted=False,
                error_message=str(e),
            )

    def _pack_long_img(
        self, source_dir: Path, output_name: str, output_dir: Path
    ) -> PackResult:
        """打包为长图：纵向拼接图片，过长自动分段，多段则打包为 ZIP"""
        if not PIL_AVAILABLE:
            return PackResult(
                success=False,
                output_path=None,
                format="long_img",
                encrypted=False,
                error_message="Pillow 库未安装，无法生成长图",
            )

        # 收集所有图片文件（按完整路径排序，保证章节/页码顺序）
        image_files: list[Path] = []
        for root, _dirs, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in _IMAGE_EXTENSIONS:
                    image_files.append(file_path)
        image_files.sort()

        if not image_files:
            return PackResult(
                success=False,
                output_path=None,
                format="long_img",
                encrypted=False,
                error_message="未找到图片文件",
            )

        try:
            strips = self._build_long_strips(image_files)
        except Exception as e:
            return PackResult(
                success=False,
                output_path=None,
                format="long_img",
                encrypted=False,
                error_message=str(e),
            )

        if not strips:
            return PackResult(
                success=False,
                output_path=None,
                format="long_img",
                encrypted=False,
                error_message="无法生成长图",
            )

        try:
            # 单段：直接输出一张长图
            if len(strips) == 1:
                output_path = output_dir / f"{output_name}.png"
                strips[0].save(output_path)
                strips[0].close()
                return PackResult(
                    success=True,
                    output_path=output_path,
                    format="long_img",
                    encrypted=False,
                )

            # 多段：先落地为多张 png，再复用 ZIP 打包逻辑（支持加密）
            import tempfile

            tmp_dir = Path(tempfile.mkdtemp(prefix="jm_longimg_"))
            try:
                for index, strip in enumerate(strips, 1):
                    strip.save(tmp_dir / f"{output_name}_{index:03d}.png")
                    strip.close()
                zip_result = self._pack_zip(tmp_dir, output_name, output_dir)
                return PackResult(
                    success=zip_result.success,
                    output_path=zip_result.output_path,
                    format="long_img",
                    encrypted=zip_result.encrypted,
                    error_message=zip_result.error_message,
                )
            finally:
                self.cleanup(tmp_dir)
        except Exception as e:
            return PackResult(
                success=False,
                output_path=None,
                format="long_img",
                encrypted=False,
                error_message=str(e),
            )

    def _build_long_strips(self, image_files: list[Path]) -> list:
        """把图片缩放到统一宽度并按高度/数量上限分段，返回拼接后的 PIL 图片列表"""
        strips = []
        batch: list = []
        batch_height = 0

        def flush_batch() -> None:
            nonlocal batch, batch_height
            if batch:
                strips.append(self._merge_vertical(batch))
                batch = []
                batch_height = 0

        for file_path in image_files:
            try:
                with Image.open(file_path) as raw:
                    scaled_height = max(
                        1, int(raw.height * _LONG_IMG_WIDTH / raw.width)
                    )
                    img = raw.convert("RGB").resize((_LONG_IMG_WIDTH, scaled_height))
            except Exception:
                continue  # 跳过无法读取的图片

            if batch and (
                batch_height + img.height > _LONG_IMG_MAX_STRIP_HEIGHT
                or len(batch) >= _LONG_IMG_MAX_PER_STRIP
            ):
                flush_batch()

            batch.append(img)
            batch_height += img.height

        flush_batch()
        return strips

    @staticmethod
    def _merge_vertical(images: list):
        """把同宽度的图片纵向拼成一张，并释放分块图片占用的内存"""
        total_height = sum(im.height for im in images)
        canvas = Image.new("RGB", (_LONG_IMG_WIDTH, total_height), (255, 255, 255))
        offset_y = 0
        for im in images:
            canvas.paste(im, (0, offset_y))
            offset_y += im.height
            im.close()
        return canvas

    @staticmethod
    def cleanup(path: Path) -> bool:
        """
        清理文件或目录

        Args:
            path: 要删除的路径

        Returns:
            是否成功删除
        """
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
            return True
        except Exception:
            return False
