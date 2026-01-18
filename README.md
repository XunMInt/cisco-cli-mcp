# Cisco CLI MCP Server

[English](#english) | [中文](#中文)

---

## English

A Telnet-based MCP tool for Cisco network device CLI, optimized for Cisco IOS devices.

### Features

- **Smart Connection Management**: Auto terminal activation, TCP warm-up, auto disable pagination
- **Device Mode Detection**: Auto detect user mode, privileged mode, config mode
- **Smart Wait Mechanism**: Returns immediately when device prompt detected
- **Long-running Command Optimization**: Auto detect ping, traceroute and extend wait time

### Tools

- **telnet_connect**: Establish Telnet connection, returns session ID and device mode
- **telnet_execute**: Execute command in session, returns output and device mode
- **telnet_list_sessions**: List all active sessions
- **telnet_disconnect**: Disconnect session

### Installation

```bash
pip install -e .
```

### Usage

#### Run as MCP Server

```bash
cisco-cli-mcp
```

#### Configure MCP Client

Add to MCP client config:

```json
{
  "mcpServers": {
    "cisco-cli-mcp": {
      "command": "cisco-cli-mcp"
    }
  }
}
```

### Response Format

#### telnet_connect

```json
{
  "success": true,
  "sessionId": "xxx-xxx-xxx",
  "deviceMode": "SW3#",
  "message": "连接成功"
}
```

#### telnet_execute

```json
{
  "success": true,
  "output": "command output...",
  "deviceMode": "SW3#"
}
```

### System Prompt

```text
You are a Cisco network device configuration assistant, skilled in configuring routers and switches.

1. You can use the cisco-cli-mcp tool to connect to devices.
2. For long-running operations like ping, traceroute, show tech-support, etc., set wait_ms to 3000-10000 milliseconds or longer.
3. When sending commands, always remember the current system mode (e.g., privileged mode, global config mode). Adjust commands based on mode (e.g., add "do" prefix for show commands in config mode, use "configure terminal" to enter config mode from privileged mode).
4. If already connected, use telnet_list_sessions to reuse existing sessions instead of reconnecting.
5. When unsure about configuration, run show commands first to verify before making changes.
6. All configurations should be based on the topology information provided by the user. Ask for clarification if anything is unclear.
7. If a command error occurs, use the "?" command to see available options.
8. Before calling a tool, briefly explain what you're about to do (no need for lengthy explanations).
```

---

## 中文

一个基于Telnet协议的思科网络设备CLI的MCP工具，专为思科IOS设备优化。

### 功能特性

- **智能连接管理**：自动激活终端、TCP预热、自动禁用分页
- **设备模式检测**：自动识别用户模式、特权模式、配置模式
- **智能等待机制**：检测到设备提示符立即返回，无需等满超时时间
- **耗时命令优化**：自动检测ping、traceroute等命令并增加等待时间

### 工具列表

- **telnet_connect**: 建立Telnet连接，返回会话ID和设备当前模式
- **telnet_execute**: 在指定会话执行命令，返回输出和设备模式
- **telnet_list_sessions**: 列出所有活动会话
- **telnet_disconnect**: 断开指定会话

### 安装

```bash
pip install -e .
```

### 使用

#### 作为MCP服务器运行

```bash
cisco-cli-mcp
```

#### 配置MCP客户端

在MCP客户端配置文件中添加：

```json
{
  "mcpServers": {
    "cisco-cli-mcp": {
      "command": "cisco-cli-mcp"
    }
  }
}
```

### 返回格式

#### telnet_connect

```json
{
  "success": true,
  "sessionId": "xxx-xxx-xxx",
  "deviceMode": "SW3#",
  "message": "连接成功"
}
```

#### telnet_execute

```json
{
  "success": true,
  "output": "命令输出内容...",
  "deviceMode": "SW3#"
}
```

### 提示词

```text
你是思科网络设备配置助手，擅长配置路由器交换机

1、你可以使用cisco-cli-mcp工具连接设备
2、对于耗时操作如 ping、traceroute、show tech-support 等，建议将此值设置为 3000-10000 毫秒或更长时间。
3、你每次发送命令的时候，务必记住当前的系统模式（例如特权模式、全局配置模式等）配置命令要根据模式进行调整（如在全局配置模式，执行show操作要加上do，在特权模式执行配置操作要configure terminal等。
4、如果之前已经连接成功的话，可以使用telnet_list_sessions工具复用之前的会话，避免二次连接
5、你不确定的配置要执行show操作进行确定再配置
6、所有的配置要结合用户给出的拓扑信息，有不清楚的地方可以反问用户。
7、如果提示命令错误，可以使用“?”命令查看提示
8、你调用工具的之前必须得简单解释一下（不需要解释太多）
```
