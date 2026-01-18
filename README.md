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
