# -*- coding: utf-8 -*-
"""机器码工具模块

用于获取当前客户端机器的唯一标识，并映射到对应的租户（部门）。

设计要点：
- 优先使用主板 UUID（Windows 上相对稳定）
- 次选 MAC 地址（跨平台，但换网卡会变）
- 最终兜底使用 uuid.getnode() 生成的节点标识
- 机器码统一格式化为十六进制字符串，便于在配置中比对
"""

import uuid
import platform
import subprocess


def get_machine_code() -> str:
    """获取当前机器的唯一标识码。

    Returns:
        str: 16进制小写机器码字符串。
    """
    code = _get_bios_uuid() or _get_mac_address()
    return code.lower()


def _get_bios_uuid() -> str | None:
    """尝试获取 Windows BIOS/主板 UUID。

    Returns:
        str | None: 成功返回 UUID 字符串，失败返回 None。
    """
    if platform.system() != "Windows":
        return None
    try:
        result = subprocess.run(
            ["wmic", "csproduct", "get", "uuid", "/value"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in result.stdout.splitlines():
            if line.strip().startswith("UUID="):
                value = line.strip().split("=", 1)[1].strip()
                if value and value.lower() != "ffffffff-ffff-ffff-ffff-ffffffffffff":
                    return value.replace("-", "")
    except Exception:
        pass
    return None


def _get_mac_address() -> str:
    """获取 MAC 地址作为机器码兜底方案。

    Returns:
        str: 12位十六进制 MAC 地址字符串。
    """
    node = uuid.getnode()
    return f"{node:012x}"


def resolve_department(machine_code: str | None = None) -> str:
    """根据机器码解析对应的部门（租户）ID。

    Args:
        machine_code: 可选，传入指定机器码；默认读取当前机器码。

    Returns:
        str: 部门 ID，如 "S" / "W" / "M" / "D"，未匹配时返回 "S"。
    """
    from config import Config

    code = machine_code or get_machine_code()
    # 2026-06-29 修复：兜底处理，防止打包后 Config 缺少 MACHINE_DEPT_MAP 时崩溃
    mapping = getattr(Config, "MACHINE_DEPT_MAP", {}) or {}
    return mapping.get(code, "S")
