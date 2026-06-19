# 4G MQTT 接入排查总结

日期：2026-05-22

## 最终结论

本次机器人无法通过 4G 上报到 MyGardenOS MQTT 服务的最终原因确认是：

**当前测试机器的 4G 模块损坏。**

这意味着前期看到的现象不是由 MQTT 服务、BLE 下发格式、服务器端口、账号密码、topic、Web 页面实现导致的。设备侧能够接收并保存 MQTT 配置，但 4G 数据链路没有正常建立，因此无法向 MQTT broker 发起连接和上报。

## 设备与服务信息

测试机器信息：

- 机器 ID：`CD145B0AE7C1`
- 型号：`FD-A902`
- eSIM ICCID：`89430103223187923518`
- 软件版本：`3.4.7.3`
- 协议版本：`1.6.1.4`
- 蓝牙版本：`V1.1.5`
- 4G 模块版本：`19001.1000.00.02.23.11`

MyGardenOS MQTT 服务：

- Railway TCP proxy host：`nozomi.proxy.rlwy.net`
- Railway TCP proxy IP：`66.33.22.249`
- Port：`53239`
- MQTT user/password：`admin/admin`
- 机器人上报 topic：`HeartBeat`
- 云端下发 topic：`RobotCommand/{robotId}`
- 机器人响应 topic：`ResponseCommand`

BLE 信息：

- Scan name：`NBMower`
- Service UUID：`fff0`
- Read/notify UUID：`fff1`
- Write UUID：`fff2`

## 已验证事项

### 1. MQTT 服务可用

我们部署了 Mosquitto MQTT broker 到 Railway，并通过 TCP proxy 暴露公网端口。

验证结果：

- 外部 MQTT 客户端可以连接 `nozomi.proxy.rlwy.net:53239`。
- 外部 MQTT 客户端可以连接 `66.33.22.249:53239`。
- `admin/admin` 可以连接。
- 发布到 `HeartBeat` 后，订阅端可以收到。
- 后端 MQTT monitor 可以订阅 `HeartBeat`、`ResponseCommand`、`$SYS/broker/log/#`。
- 厂家另一台机器可以使用我们的 IP 和端口上报。

因此可以排除 MyGardenOS MQTT broker、Railway TCP proxy、topic 名称、账号密码这几个方向的问题。

### 2. BLE 下发通道可用

我们做了独立 Web Bluetooth 工具：

`tools/ble-mqtt-config/index.html`

功能包括：

- 连接 `NBMower`
- 写入 MQTT `$AT` 配置
- 读取 `$AT,0`
- 读取 `$SYSTEM`
- 读取 `$STATUS`
- 读取 `$CONFIG,0`
- 打开 4G：`$CONFIG,1,304,1`
- 自检：`$ACTION,4`
- 待机：`$ACTION,6`
- 遥控模式：`$ACTION,0`
- 查看 BLE RX/TX 日志
- 查看 MQTT broker logs 和业务消息

确认 BLE UUID 与厂家提供一致：

```text
Service UUID: fff0
Read/notify UUID: fff1
Write UUID: fff2
```

### 3. MQTT 配置写入格式正确

正常发送格式：

```text
{"command":"$AT,1,10,66.33.22.249,53239,admin,admin"}\r\n
```

读取配置：

```text
{"command":"$AT,0"}\r\n
```

设备返回过：

```text
{"command":"$AT,0","data":"10,linksnet,66.33.22.249,53239,admin,admin,0.1","code":"00","message":"success"}\r\n
```

这说明设备已经保存了 MQTT host、port、username、password。

### 4. 转义符不是实际发送内容

厂家给过类似格式：

```text
"{\"command\":\"\(command)\"}\r\n"
```

我们验证后确认，这只是代码字符串写法，不是 BLE 实际要发送的字节。

错误实验发送：

```text
{\"command\":\"$AT,1,10,nozomi.proxy.rlwy.net,53239,admin,admin\"}\r\n
```

设备返回：

```text
下发不成功
```

结论：

- 正确实际字节是普通 JSON 文本加 CRLF。
- 不应该把反斜杠 `\` 作为实际 BLE 内容发送。

### 5. BLE 写入方式已对齐厂家示例

厂家示例使用：

```js
await writeChar.writeValueWithoutResponse(bytes);
```

我们最初优先使用 `writeValueWithResponse`，后来已改为优先使用：

```js
writeValueWithoutResponse(bytes)
```

同时扫描方式也从 `namePrefix: 'NBMower'` 改为：

```js
filters: [{ name: 'NBMower' }]
```

改完后问题依旧存在，因此可以排除 Web Bluetooth 写入方式差异。

### 6. 4G 开关有效，但 4G 数据链路未正常建立

读取配置：

```text
{"command":"$CONFIG,0"}\r\n
```

协议中第 17 个字段是 4G 开关。

实际返回中该字段为 `1`，说明 4G 开关打开。

用户实际观察：

- 关闭 4G 后，信号塔图标消失。
- 打开 4G 后，能找到信号塔。
- 但机器上的 4G 图标始终不亮。

这说明 4G 开关和模块扫描可能是有效的，但数据网络没有真正进入可用状态。

### 7. 物理重启不能恢复

用户已经物理重启设备。

重启后问题仍然存在：

- 改到 MyGardenOS MQTT 不上报。
- 改回厂家 MQTT 也不上报。
- 4G 图标仍不亮。

这排除了“写入 `$AT` 后必须重启才生效”这一常见原因。

## 踩过的坑

### 1. 把 BLE 心跳误认为 MQTT 上报

遥控模式下，设备会通过 BLE 推送：

```text
{"command":"$HEARTBEAT", ...}
```

这只是 BLE 通道心跳，不是 MQTT topic `HeartBeat`。

判断是否云端上报，必须看 MQTT broker 是否收到：

```text
HeartBeat
ResponseCommand
```

### 2. `success` 只代表配置写入成功，不代表 4G/MQTT 已连接

例如：

```text
{"code":"00","message":"success"}
```

只能说明设备解析并保存了命令。

它不能说明：

- SIM 已注册网络
- APN 正确
- PDP 数据连接成功
- MQTT 已连接
- HeartBeat 已上报

### 3. `4G开关=1` 不等于 4G 已联网

`$CONFIG,0` 只能读取 4G 开关状态。

协议没有提供：

- SIM 注册状态
- 信号强度
- APN
- PDP 状态
- MQTT 连接状态
- 最近一次 MQTT 错误码

因此 4G 开关打开以后仍需要结合设备屏幕图标、厂家后台和 MQTT broker logs 判断。

### 4. 不要把代码里的转义符当成实际 BLE 内容

代码里可能写：

```text
"{\"command\":\"$STATUS\"}\r\n"
```

实际发送应是：

```text
{"command":"$STATUS"}\r\n
```

如果实际发送 `{\"command\"...`，设备会认为格式错误。

### 5. 只看网页没用，要同时看 broker logs

为了排查是否真的有 MQTT 流量，需要订阅：

```bash
mosquitto_sub -h nozomi.proxy.rlwy.net -p 53239 -u admin -P admin -t '#' -v
```

以及 broker logs：

```bash
mosquitto_sub -h nozomi.proxy.rlwy.net -p 53239 -u admin -P admin -t '$SYS/broker/log/#' -v
```

这样可以区分：

- 后端页面没刷新
- 后端 monitor 没收到
- broker 本身没收到连接
- MQTT 客户端连上但没 publish

### 6. QoS 0 的云端命令不会离线排队

我们发送过：

```text
RobotCommand/CD145B0AE7C1
```

如果机器人当时没有在线订阅该 topic，QoS 0 消息不会排队保存。

所以没有收到 `ResponseCommand` 并不一定说明命令格式错，更可能说明设备根本不在线。

## 本次新增工具与能力

### Web Bluetooth MQTT Config Tool

路径：

```text
tools/ble-mqtt-config/index.html
```

运行：

```bash
cd tools/ble-mqtt-config
python3 -m http.server 4173
```

访问：

```text
http://localhost:4173
```

说明：

- Chrome/Edge 支持 Web Bluetooth。
- iOS 浏览器和 iOS Simulator 不支持 Web Bluetooth。
- BLE 配置可独立使用。
- MQTT monitor 依赖 Railway backend。

### Backend MQTT Monitor

后端订阅：

```text
HeartBeat
ResponseCommand
$SYS/broker/log/#
```

公开只读接口：

```text
GET /iot/mqtt/public/status
GET /iot/mqtt/public/messages
POST /iot/mqtt/public/messages/clear
```

登录后可下发云端命令：

```text
POST /iot/mqtt/robot-command
```

### MQTT Broker

路径：

```text
mqtt/
```

Railway 部署使用：

```text
Dockerfile Path: mqtt/Dockerfile
```

当前测试 broker 允许匿名连接，适合 bring-up，不适合长期生产使用。

## 后续接入新设备的标准排查顺序

1. 读取 `$SYSTEM`
   - 确认机器 ID、ICCID、4G 模块版本。

2. 读取 `$CONFIG,0`
   - 确认 4G 开关字段是否为 `1`。

3. 写入 `$AT`
   - 使用 IP 优先，避免 DNS 干扰。
   - 格式为普通 JSON + `\r\n`。

4. 读取 `$AT,0`
   - 确认设备已保存 host、port、username、password。

5. 观察设备 4G 图标
   - 4G 图标不亮时，优先查设备网络，不要继续纠结 MQTT。

6. 监听 MQTT broker
   - `#`
   - `$SYS/broker/log/#`
   - `HeartBeat`
   - `ResponseCommand`

7. 发送云端探针
   - 向 `RobotCommand/{robotId}` 发送 `$SYSTEM`
   - 等待 `ResponseCommand`

8. 若设备不上线，要求厂家提供：
   - 4G/SIM 注册状态
   - APN
   - PDP 数据连接状态
   - MQTT 连接状态
   - 最近一次 MQTT 错误码
   - 重启 4G 模块或恢复网络模块指令

## 厂家沟通要点模板

```text
机器 ID:
ICCID:
型号:
4G 模块版本:

已确认：
1. $AT 写入 MQTT 配置返回 success
2. $AT,0 能读回正确配置
3. $CONFIG,0 显示 4G 开关为 1
4. 已物理重启
5. MQTT broker 已验证可用
6. 其他机器可上报到同一 MQTT broker
7. 当前机器不上报，且设备 4G 图标不亮

请确认：
1. 该机器 4G 模块是否正常
2. eSIM 是否激活、有流量、未停机
3. 是否已完成网络注册
4. PDP 数据连接是否成功
5. 是否存在 APN 或白名单限制
6. 是否有 MQTT 连接错误日志
7. 是否可以后台重置该设备网络状态
```

## 本次结论回顾

本次排查从 AWS IoT 接入准备开始，逐步切到更适合设备现状的自建 MQTT broker。通过 BLE 写入 `$AT`、Railway MQTT broker、后端 MQTT monitor、Web Bluetooth 工具、厂家对照机器测试等方式，最终确认云端和协议链路都是可行的。

真正的问题是当前测试机器硬件侧 4G 模块损坏，导致设备无法完成 4G MQTT 上报。
