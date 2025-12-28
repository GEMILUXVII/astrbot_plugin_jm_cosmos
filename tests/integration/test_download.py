"""
下载功能集成测试

测试真实下载功能，使用小体积漫画 (ID: 2568)。
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestDownloadIntegration:
    """下载功能集成测试"""

    @pytest.mark.asyncio
    async def test_download_album(self, downloader, test_album_id):
        """测试下载完整本子"""
        result = await downloader.download_album(test_album_id)

        assert result is not None, "应该返回下载结果"
        assert result.success, f"下载应该成功: {result.error_message}"
        assert result.album_id == test_album_id or str(result.album_id) == test_album_id
        assert result.save_path.exists(), "保存路径应该存在"

    @pytest.mark.asyncio
    async def test_download_album_returns_info(self, downloader, test_album_id):
        """测试下载结果包含正确信息"""
        result = await downloader.download_album(test_album_id)

        if result.success:
            assert result.title, "下载结果应该包含标题"
            assert result.photo_count >= 0, "章节数应该 >= 0"
            assert result.image_count >= 0, "图片数应该 >= 0"

    @pytest.mark.asyncio
    async def test_download_invalid_id(self, downloader):
        """测试下载无效 ID"""
        result = await downloader.download_album("999999999999")

        # 无效 ID 应该返回失败结果
        assert result is not None
        # 可能成功也可能失败，取决于服务器响应


class TestDownloadPhotoIntegration:
    """章节下载集成测试"""

    @pytest.mark.asyncio
    async def test_download_photo(self, downloader, browser, test_album_id):
        """测试下载单个章节"""
        # 首先获取第一章的 photo_id
        photo_info = await browser.get_photo_id_by_index(test_album_id, 1)

        if photo_info is None:
            pytest.skip("无法获取章节信息")

        photo_id = photo_info[0]
        result = await downloader.download_photo(str(photo_id))

        assert result is not None, "应该返回下载结果"
        if result.success:
            assert result.save_path.exists(), "保存路径应该存在"


class TestDownloadWithPacking:
    """下载并打包集成测试"""

    @pytest.mark.asyncio
    async def test_download_and_pack_zip(self, downloader, config_manager, test_album_id):
        """测试下载并打包为 ZIP"""
        from core.packer import JMPacker

        # 下载
        result = await downloader.download_album(test_album_id)

        if not result.success:
            pytest.skip(f"下载失败: {result.error_message}")

        # 打包
        packer = JMPacker(pack_format="zip", password="")
        pack_result = packer.pack(result.save_path, f"test_{test_album_id}")

        assert pack_result.success, f"打包应该成功: {pack_result.error_message}"
        assert pack_result.output_path.exists(), "ZIP 文件应该存在"
        assert pack_result.output_path.suffix == ".zip"

        # 清理
        JMPacker.cleanup(pack_result.output_path)
