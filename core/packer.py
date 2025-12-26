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

        try:
            if self.password and PYZIPPER_AVAILABLE:
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
                encrypted=bool(self.password and PYZIPPER_AVAILABLE),
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
