# BLE MQTT config web tool

This is a browser-based test page for writing the robot MQTT `$AT` command over BLE.

It uses Web Bluetooth, so use Chrome or Edge on Mac/Windows/Android. iPhone/iPad Safari, Chrome on iOS, and iOS Simulator cannot scan or connect to BLE devices from a web page.

Run locally:

```bash
cd apps/mygardenos/tools/ble-mqtt-config
python3 -m http.server 4173
```

Open:

```text
http://localhost:4173
```

The page connects to:

```text
Scan name: NBMower
Service UUID: fff0
Read/notify UUID: fff1
Write UUID: fff2
```

Default command:

```json
{"command":"$AT,1,10,nozomi.proxy.rlwy.net,53239,admin,admin"}\r\n
```

The page also includes a backend monitor. Log in with a MyGardenOS account to poll:

```text
/iot/mqtt/status
/iot/mqtt/messages
```

This shows robot messages plus Mosquitto broker logs published under `$SYS/broker/log/#`.
