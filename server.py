"""
Telnet MCP Server

A Model Context Protocol server for Telnet session management.
Provides tools for connecting, executing commands, listing sessions, and disconnecting.
"""

import asyncio
import uuid
import re
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

import telnetlib3
from mcp.server.fastmcp import FastMCP

# 创建FastMCP实例
mcp = FastMCP("Cisco CLI MCP Server")


def detect_device_mode(output: str) -> str:
    """
    从输出中检测设备当前模式
    
    Returns:
        设备模式字符串，如 "SW3#"（特权模式）、"SW3>"（用户模式）、
        "SW3(config)#"（全局配置模式）、"SW3(config-if)#"（接口配置模式）等
    """
    if not output:
        return "unknown"
    
    # 匹配思科设备的提示符模式
    # 例如: SW3#, SW3>, SW3(config)#, SW3(config-if)#, SW3(config-router)#
    patterns = [
        r'[\r\n]([A-Za-z0-9_-]+\([a-z0-9-]+\)[#>])\s*$',  # 配置模式: SW3(config)#
        r'[\r\n]([A-Za-z0-9_-]+[#>])\s*$',                  # 特权/用户模式: SW3# 或 SW3>
    ]
    
    # 清理输出中的控制字符
    clean_output = output.replace('\x08', '').replace(' \b', '')
    
    for pattern in patterns:
        match = re.search(pattern, clean_output)
        if match:
            return match.group(1).strip()
    
    # 如果没匹配到，尝试从最后几行查找
    lines = clean_output.strip().split('\n')
    for line in reversed(lines[-5:]):
        line = line.strip()
        if re.match(r'^[A-Za-z0-9_-]+(\([a-z0-9-]+\))?[#>]$', line):
            return line
    
    return "unknown"


@dataclass
class TelnetSession:
    """表示一个Telnet会话"""
    session_id: str
    host: str
    port: int
    reader: telnetlib3.TelnetReader
    writer: telnetlib3.TelnetWriter
    connected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "sessionId": self.session_id,
            "host": self.host,
            "port": self.port,
            "connectedAt": self.connected_at.isoformat(),
        }


class TelnetSessionManager:
    """Telnet会话管理器"""

    def __init__(self):
        self.sessions: dict[str, TelnetSession] = {}

    async def connect(
        self, host: str, port: int, timeout: int = 5000
    ) -> str:
        """
        建立Telnet连接

        Args:
            host: 主机地址
            port: 端口号
            timeout: 连接超时时间（毫秒）

        Returns:
            会话ID
        """
        timeout_seconds = timeout / 1000.0

        try:
            reader, writer = await asyncio.wait_for(
                telnetlib3.open_connection(host, port),
                timeout=timeout_seconds
            )

            session_id = str(uuid.uuid4())
            session = TelnetSession(
                session_id=session_id,
                host=host,
                port=port,
                reader=reader,
                writer=writer,
            )
            self.sessions[session_id] = session

            # 先发送回车键激活终端
            # 处理设备可能处于 "Press RETURN to get started" 状态
            for i in range(3):
                writer.write("\r\n")
                await writer.drain()
                await asyncio.sleep(0.1)

            # TCP 预热：发送 ? 命令来热身 TCP 连接
            # ? 命令在任何模式下都有效，并且会产生大量输出
            for i in range(5):
                writer.write("?\r\n")
                await writer.drain()
                await asyncio.sleep(0.3)
            
            # 丢弃预热过程中的输出并检测当前模式
            initial_output = ""
            try:
                while True:
                    data = await asyncio.wait_for(reader.read(4096), timeout=0.1)
                    if not data:
                        break
                    initial_output += data
            except asyncio.TimeoutError:
                pass

            # 检测是否处于配置模式，如果是则先退出到特权模式
            if '(config' in initial_output:
                # 可能处于配置模式，发送end命令退出到特权模式
                writer.write("end\r\n")
                await writer.drain()
                await asyncio.sleep(0.3)
                # 丢弃end命令的输出
                try:
                    while True:
                        data = await asyncio.wait_for(reader.read(4096), timeout=0.1)
                        if not data:
                            break
                except asyncio.TimeoutError:
                    pass

            # 自动设置 terminal length 0 禁用分页
            # 此命令在用户模式和特权模式下都有效
            writer.write("terminal length 0\r\n")
            await writer.drain()
            await asyncio.sleep(0.3)
            
            # 丢弃 terminal length 0 的输出
            try:
                while True:
                    data = await asyncio.wait_for(reader.read(4096), timeout=0.1)
                    if not data:
                        break
            except asyncio.TimeoutError:
                pass

            return session_id

        except asyncio.TimeoutError:
            raise ConnectionError(f"连接超时: {host}:{port}")
        except Exception as e:
            raise ConnectionError(f"连接失败: {host}:{port} - {str(e)}")

    async def execute(
        self, session_id: str, command: str, wait_ms: int = 2000
    ) -> str:
        """
        在指定会话执行命令

        Args:
            session_id: 会话ID
            command: 要发送的命令
            wait_ms: 数据等待时间（毫秒，默认2000）
                     对于耗时操作会自动增加等待时间

        Returns:
            命令输出
        """
        
        if session_id not in self.sessions:
            raise ValueError(f"会话不存在: {session_id}")

        session = self.sessions[session_id]
        
        # 自动检测耗时命令并调整等待时间
        command_lower = command.lower().strip()
        long_running_commands = [
            'ping',           # ping 默认5个包，每个超时2秒 -> 需要约12秒
            'traceroute',     # traceroute 可能需要较长时间
            'tracert',        # Windows风格
            'show tech',      # show tech-support 输出很长
            'copy',           # 复制操作
            'write',          # 写入操作
            'reload',         # 重启操作
            'debug',          # 调试命令
        ]
        
        # 如果检测到耗时命令，自动增加等待时间（至少12秒）
        for cmd in long_running_commands:
            if command_lower.startswith(cmd):
                wait_ms = max(wait_ms, 12000)
                break
        
        wait_seconds = wait_ms / 1000.0

        # 发送命令
        session.writer.write(command + "\r\n")
        await session.writer.drain()

        output = ""
        start_time = asyncio.get_event_loop().time()
        last_data_time = start_time

        # 设备提示符正则模式（用于检测命令执行完成）
        prompt_pattern = re.compile(r'[\r\n]([A-Za-z0-9_-]+(\([a-z0-9-]+\))?[#>])\s*$')

        while True:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time

            if elapsed >= wait_seconds:
                break

            try:
                # 使用较短的超时进行非阻塞式读取
                data = await asyncio.wait_for(
                    session.reader.read(4096),
                    timeout=0.1
                )
                if data:
                    output += data
                    last_data_time = current_time
                    
                    # 检测设备提示符，如果检测到则认为命令执行完成
                    clean_output = output.replace('\x08', '').replace(' \b', '')
                    if prompt_pattern.search(clean_output):
                        # 再等待一小段时间确保没有更多数据
                        await asyncio.sleep(0.2)
                        try:
                            extra_data = await asyncio.wait_for(
                                session.reader.read(4096),
                                timeout=0.1
                            )
                            if extra_data:
                                output += extra_data
                        except asyncio.TimeoutError:
                            pass
                        break
                        
            except asyncio.TimeoutError:
                # 检查沉默时间，如果沉默超过1秒且已有输出，检查是否有提示符
                silence_duration = current_time - last_data_time
                if silence_duration >= 1.0 and output:
                    clean_output = output.replace('\x08', '').replace(' \b', '')
                    if prompt_pattern.search(clean_output):
                        break

            except Exception:
                pass

        return output

    def list_sessions(self) -> list[dict]:
        """
        列出所有活动会话

        Returns:
            会话信息数组
        """
        return [session.to_dict() for session in self.sessions.values()]

    async def disconnect(self, session_id: str) -> bool:
        """
        断开指定会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功断开
        """
        if session_id not in self.sessions:
            raise ValueError(f"会话不存在: {session_id}")

        session = self.sessions[session_id]

        try:
            session.writer.close()
        except Exception:
            pass

        del self.sessions[session_id]
        return True


# 全局会话管理器实例
session_manager = TelnetSessionManager()


# ============ MCP 工具定义 ============

@mcp.tool()
async def telnet_connect(host: str, port: int, timeout: int = 5000) -> str:
    """
    建立Telnet连接

    Args:
        host: 主机地址
        port: 端口号
        timeout: 连接超时时间（毫秒，默认5000）

    Returns:
        连接结果，包含会话ID和设备当前模式
        设备模式说明：
        - "SW3>" 表示用户模式，需要执行 enable 进入特权模式
        - "SW3#" 表示特权模式，可以执行 show 命令
        - "SW3(config)#" 表示全局配置模式
        - "SW3(config-if)#" 表示接口配置模式
        - "SW3(config-router)#" 表示路由配置模式
    """
    try:
        session_id = await session_manager.connect(host, port, timeout)
        # 发送空命令获取当前提示符
        initial_output = await session_manager.execute(session_id, "", 1000)
        device_mode = detect_device_mode(initial_output)
        return json.dumps({
            "success": True,
            "sessionId": session_id,
            "deviceMode": device_mode,
            "message": "连接成功"
        }, ensure_ascii=False)
    except ConnectionError as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@mcp.tool()
async def telnet_execute(session_id: str, command: str, wait_ms: int = 2000) -> str:
    """
    在指定会话执行命令

    Args:
        session_id: 会话ID
        command: 要发送的命令
        wait_ms: 最大等待时间（毫秒，默认2000）
                 系统会智能检测设备提示符，检测到后立即返回，无需等满超时时间。
                 对于 ping、traceroute 等耗时命令，系统会自动增加等待时间至12秒。

    Returns:
        命令输出（JSON格式）
        - success: 是否成功
        - output: 命令输出内容
        - deviceMode: 当前设备模式（如 SW3#、SW3>、SW3(config)# 等）
    """
    try:
        output = await session_manager.execute(session_id, command, wait_ms)
        device_mode = detect_device_mode(output)
        return json.dumps({
            "success": True,
            "output": output if output else "",
            "deviceMode": device_mode
        }, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    except RuntimeError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool()
def telnet_list_sessions() -> str:
    """
    列出所有活动会话

    Returns:
        会话信息（JSON格式）
    """
    sessions = session_manager.list_sessions()
    if not sessions:
        return "当前没有活动会话"

    result = "活动会话列表:\n"
    for session in sessions:
        result += f"- ID: {session['sessionId']}\n"
        result += f"  主机: {session['host']}:{session['port']}\n"
        result += f"  连接时间: {session['connectedAt']}\n"
    return result


@mcp.tool()
async def telnet_disconnect(session_id: str) -> str:
    """
    断开指定会话

    Args:
        session_id: 会话ID

    Returns:
        断开结果
    """
    try:
        await session_manager.disconnect(session_id)
        return f"会话 {session_id} 已断开"
    except ValueError as e:
        return f"错误: {str(e)}"


def main():
    """入口函数"""
    mcp.run()


if __name__ == "__main__":
    main()
