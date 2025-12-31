"""
vnpy_emt 兼容性补丁
修复 onDisconnected() 方法缺少 reason 参数的问题
"""
from vnpy_emt.api import MdApi, TdApi


class PatchedMdApi(MdApi):
    """修复后的行情API"""

    def onDisconnected(self, reason: int = 0) -> None:
        """
        服务器连接断开回报
        添加默认参数以兼容底层C++调用
        """
        pass


class PatchedTdApi(TdApi):
    """修复后的交易API"""

    def onDisconnected(self, session: int = 0, reason: int = 0) -> None:
        """
        服务器连接断开回报
        添加默认参数以兼容底层C++调用
        """
        pass


def apply_patch():
    """应用补丁到 vnpy_emt"""
    import vnpy_emt.api as api_module

    # 保存原始类
    original_md_api = api_module.MdApi
    original_td_api = api_module.TdApi

    # 创建包装类
    class WrappedMdApi(original_md_api):
        def onDisconnected(self, reason: int = 0) -> None:
            """添加默认参数"""
            super().onDisconnected(reason)

    class WrappedTdApi(original_td_api):
        def onDisconnected(self, session: int = 0, reason: int = 0) -> None:
            """添加默认参数"""
            super().onDisconnected(session, reason)

    # 替换原始类
    api_module.MdApi = WrappedMdApi
    api_module.TdApi = WrappedTdApi

    print("[补丁] vnpy_emt 兼容性补丁已应用")
    return True
