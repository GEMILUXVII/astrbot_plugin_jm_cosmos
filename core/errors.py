"""
jmcomic 异常分类

把底层 jmcomic 异常映射为面向用户的错误类型与提示，
便于上层给出比裸异常字符串更有用的反馈。
"""

from __future__ import annotations

from .jmcomic_loader import import_jmcomic

# 网络类异常关键词（用于无法精确归类时的兜底判断）
_NETWORK_KEYWORDS = ("timeout", "connect", "network", "ssl", "proxy", "max retries")


def classify_exception(exc: BaseException) -> tuple[str, str]:
    """
    将异常映射为 (error_type, 用户提示)。

    error_type 与 MessageFormatter.format_error 的键保持一致
    (not_found / network / download_failed)。
    """
    jmcomic = import_jmcomic()
    if jmcomic is not None:
        missing = getattr(jmcomic, "MissingAlbumPhotoException", None)
        retry_fail = getattr(jmcomic, "RequestRetryAllFailException", None)
        partial = getattr(jmcomic, "PartialDownloadFailedException", None)

        if missing is not None and isinstance(exc, missing):
            return "not_found", "未找到该本子或章节，请检查ID是否正确"
        if retry_fail is not None and isinstance(exc, retry_fail):
            return (
                "network",
                "请求多次重试均失败，可能是域名被墙或网络问题，"
                "可尝试配置代理或自定义域名",
            )
        if partial is not None and isinstance(exc, partial):
            return "download_failed", "部分图片下载失败"

    msg = str(exc) or exc.__class__.__name__
    if any(keyword in msg.lower() for keyword in _NETWORK_KEYWORDS):
        return "network", "网络连接失败，请稍后重试"
    return "download_failed", msg
