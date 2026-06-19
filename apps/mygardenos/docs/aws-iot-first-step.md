# AWS IoT first step

This project now keeps the current robot protocol documents in:

- `docs/protocols/通讯协议精简版.md`
- `docs/protocols/ymodem升级文档.md`

## Can we complete step 1 with only these protocols?

Partly.

The MQTT protocol document is enough to define the cloud message shape:

- Robot publishes heartbeat to `HeartBeat`.
- Server publishes commands to `RobotCommand/{robotId}`.
- Robot publishes command responses to `ResponseCommand`.
- Command payloads reuse the Bluetooth command body, such as `$SYSTEM`, `$STATUS`, `$ACTION,7`, `$ACTION,8`, and `$ACTION,9`.

But the protocol documents alone are not enough to physically connect the robot to AWS IoT. We still need one device-side access method:

- SSH or command-line access to the robot.
- USB/serial access to write config or run diagnostics.
- A firmware/configuration tool from the robot vendor.
- BLE support in firmware for writing cloud endpoint/certificates.

## Practical first step

Use the AWS IoT console to create one Thing whose name is the robot `robotId`, then download the certificate package.

Before we can install that package on the robot, confirm with firmware/hardware:

1. Does the robot already have an MQTT client?
2. Where should AWS IoT certificates be stored?
3. How are `endpoint`, `thingName/clientId`, and topics configured?
4. Is the robot configured through SSH, USB/serial, BLE, or a vendor tool?

Until one of those access methods is confirmed, backend/App work can prepare the MQTT command mapping, but the real AWS connection test cannot be completed on the robot.

## BLE configuration channel

The robot vendor confirmed the BLE connection details:

```text
Scan name: NBMower
Service UUID: fff0
Read/notify UUID: fff1
Write UUID: fff2
```

This means the mobile app can configure MQTT during binding by connecting to `NBMower`, writing `$AT` commands to characteristic `fff2`, and reading or subscribing for responses from characteristic `fff1`.

## Initial command mapping

| App action | Robot command |
| --- | --- |
| Get system info | `$SYSTEM` |
| Get status | `$STATUS` |
| Pause | `$ACTION,7` |
| Resume | `$ACTION,8` |
| Return to charge | `$ACTION,9` |
| Standby | `$ACTION,6` |
| Remote mode | `$ACTION,0` |
