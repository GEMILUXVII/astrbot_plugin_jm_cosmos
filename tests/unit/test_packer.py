"""
打包器测试

测试 core/packer.py 中的 JMPacker 类和 PackResult 数据类。
"""

import os
import zipfile
from pathlib import Path

import pytest


class TestPackResult:
    """PackResult 数据类测试"""

    def test_pack_result_success(self):
        """测试成功的打包结果"""
        from core.packer import PackResult

        result = PackResult(
            success=True,
            output_path=Path("/some/path/output.zip"),
            format="zip",
            encrypted=False,
        )
        assert result.success is True
        assert result.format == "zip"
        assert result.encrypted is False
        assert result.error_message is None

    def test_pack_result_failure(self):
        """测试失败的打包结果"""
        from core.packer import PackResult

        result = PackResult(
            success=False,
            output_path=None,
            format="pdf",
            encrypted=False,
            error_message="源目录不存在",
        )
        assert result.success is False
        assert result.output_path is None
        assert result.error_message == "源目录不存在"


class TestJMPackerInit:
    """JMPacker 初始化测试"""

    def test_default_init(self):
        """测试默认初始化"""
        from core.packer import JMPacker

        packer = JMPacker()
        assert packer.pack_format == "zip"
        assert packer.password == ""

    def test_custom_init(self):
        """测试自定义初始化"""
        from core.packer import JMPacker

        packer = JMPacker(pack_format="PDF", password="secret")
        assert packer.pack_format == "pdf"  # 应转为小写
        assert packer.password == "secret"


class TestJMPackerZip:
    """JMPacker ZIP 打包测试"""

    def test_pack_zip_success(self, temp_dir):
        """测试 ZIP 打包成功"""
        from core.packer import JMPacker

        # 创建源目录和测试文件
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        (source_dir / "test1.jpg").write_bytes(b"fake image 1")
        (source_dir / "test2.jpg").write_bytes(b"fake image 2")

        packer = JMPacker(pack_format="zip")
        result = packer.pack(source_dir, "test_output", temp_dir)

        assert result.success is True
        assert result.format == "zip"
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.output_path.suffix == ".zip"

        # 验证 ZIP 内容
        with zipfile.ZipFile(result.output_path, "r") as zf:
            names = zf.namelist()
            assert "test1.jpg" in names
            assert "test2.jpg" in names

    def test_pack_zip_nested_directory(self, temp_dir):
        """测试嵌套目录的 ZIP 打包"""
        from core.packer import JMPacker

        # 创建嵌套目录
        source_dir = temp_dir / "source"
        sub_dir = source_dir / "chapter1"
        sub_dir.mkdir(parents=True)
        (sub_dir / "page1.jpg").write_bytes(b"fake image")

        packer = JMPacker(pack_format="zip")
        result = packer.pack(source_dir, "nested_output", temp_dir)

        assert result.success is True
        with zipfile.ZipFile(result.output_path, "r") as zf:
            names = zf.namelist()
            # 检查包含子目录路径
            assert any("chapter1" in name for name in names)


class TestJMPackerErrors:
    """JMPacker 错误处理测试"""

    def test_pack_nonexistent_source(self, temp_dir):
        """测试源目录不存在"""
        from core.packer import JMPacker

        packer = JMPacker()
        result = packer.pack(temp_dir / "nonexistent", "output")

        assert result.success is False
        assert "不存在" in result.error_message

    def test_pack_unsupported_format(self, temp_dir):
        """测试不支持的格式"""
        from core.packer import JMPacker

        source_dir = temp_dir / "source"
        source_dir.mkdir()

        packer = JMPacker(pack_format="rar")
        result = packer.pack(source_dir, "output")

        assert result.success is False
        assert "不支持" in result.error_message


class TestJMPackerNone:
    """JMPacker none 格式测试"""

    def test_pack_none_format(self, temp_dir):
        """测试 none 格式直接返回源目录"""
        from core.packer import JMPacker

        source_dir = temp_dir / "source"
        source_dir.mkdir()

        packer = JMPacker(pack_format="none")
        result = packer.pack(source_dir, "output")

        assert result.success is True
        assert result.format == "none"
        assert result.output_path == source_dir
        assert result.encrypted is False


class TestJMPackerCleanup:
    """JMPacker cleanup 静态方法测试"""

    def test_cleanup_file(self, temp_dir):
        """测试清理文件"""
        from core.packer import JMPacker

        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists()

        result = JMPacker.cleanup(test_file)
        assert result is True
        assert not test_file.exists()

    def test_cleanup_directory(self, temp_dir):
        """测试清理目录"""
        from core.packer import JMPacker

        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        assert test_dir.exists()

        result = JMPacker.cleanup(test_dir)
        assert result is True
        assert not test_dir.exists()

    def test_cleanup_nonexistent(self, temp_dir):
        """测试清理不存在的路径"""
        from core.packer import JMPacker

        nonexistent = temp_dir / "nonexistent"
        result = JMPacker.cleanup(nonexistent)
        # cleanup 方法逻辑：如果 is_dir() 和 is_file() 都为 False，
        # 则不执行任何删除操作，但也不会抛出异常，因此返回 True
        assert result is True
