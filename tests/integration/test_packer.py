"""
打包功能集成测试

测试真实的 ZIP/PDF 打包功能，包括有密码和无密码情况。
"""

import importlib
import zipfile
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


# 直接检测库是否可用，不依赖 packer 模块的常量
def is_pyzipper_available():
    return importlib.util.find_spec("pyzipper") is not None


def is_pymupdf_available():
    return importlib.util.find_spec("fitz") is not None


class TestZipPackingIntegration:
    """ZIP 打包集成测试"""

    def test_pack_zip_without_password(self, temp_download_dir):
        """测试无密码 ZIP 打包"""
        # 重新加载 packer 模块确保使用真实库
        import core.packer
        importlib.reload(core.packer)
        from core.packer import JMPacker

        # 创建测试文件
        source_dir = temp_download_dir / "source_zip"
        source_dir.mkdir(exist_ok=True)
        (source_dir / "image1.jpg").write_bytes(b"fake image content 1")
        (source_dir / "image2.jpg").write_bytes(b"fake image content 2")

        packer = JMPacker(pack_format="zip", password="")
        result = packer.pack(source_dir, "test_no_password", temp_download_dir)

        assert result.success is True, f"打包失败: {result.error_message}"
        assert result.format == "zip"
        assert result.encrypted is False
        assert result.output_path.exists()
        assert result.output_path.suffix == ".zip"

        # 验证 ZIP 内容可以不用密码读取
        with zipfile.ZipFile(result.output_path, "r") as zf:
            names = zf.namelist()
            assert "image1.jpg" in names
            assert "image2.jpg" in names

    def test_pack_zip_with_password(self, temp_download_dir):
        """测试带密码 ZIP 打包"""
        if not is_pyzipper_available():
            pytest.skip("pyzipper 不可用")

        # 重新加载 packer 模块
        import core.packer
        importlib.reload(core.packer)
        from core.packer import JMPacker

        source_dir = temp_download_dir / "source_zip_pwd"
        source_dir.mkdir(exist_ok=True)
        (source_dir / "secret.jpg").write_bytes(b"secret content")

        packer = JMPacker(pack_format="zip", password="testpassword123")
        result = packer.pack(source_dir, "test_with_password", temp_download_dir)

        assert result.success is True, f"打包失败: {result.error_message}"
        assert result.format == "zip"
        assert result.encrypted is True
        assert result.output_path.exists()


class TestPdfPackingIntegration:
    """PDF 打包集成测试"""

    def _create_test_image(self, path: Path):
        """创建测试用 PNG 图片"""
        # 1x1 白色像素 PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
            0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        path.write_bytes(png_data)

    def test_pack_pdf_without_password(self, temp_download_dir):
        """测试无密码 PDF 打包"""
        if not is_pymupdf_available():
            pytest.skip("pymupdf 不可用")

        import core.packer
        importlib.reload(core.packer)
        from core.packer import JMPacker

        source_dir = temp_download_dir / "source_pdf"
        source_dir.mkdir(exist_ok=True)
        self._create_test_image(source_dir / "page1.png")

        packer = JMPacker(pack_format="pdf", password="")
        result = packer.pack(source_dir, "test_pdf_no_pwd", temp_download_dir)

        assert result.success is True, f"打包失败: {result.error_message}"
        assert result.format == "pdf"
        assert result.encrypted is False
        assert result.output_path.suffix == ".pdf"
        assert result.output_path.exists()

    def test_pack_pdf_with_password(self, temp_download_dir):
        """测试带密码 PDF 打包"""
        if not is_pymupdf_available():
            pytest.skip("pymupdf 不可用")

        import core.packer
        importlib.reload(core.packer)
        from core.packer import JMPacker

        source_dir = temp_download_dir / "source_pdf_pwd"
        source_dir.mkdir(exist_ok=True)
        self._create_test_image(source_dir / "secure.png")

        packer = JMPacker(pack_format="pdf", password="pdfpassword")
        result = packer.pack(source_dir, "test_pdf_pwd", temp_download_dir)

        assert result.success is True, f"打包失败: {result.error_message}"
        assert result.format == "pdf"
        assert result.encrypted is True
        assert result.output_path.exists()
