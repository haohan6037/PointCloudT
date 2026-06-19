# Local MQTT robot test

Use this before deploying an EC2 MQTT node.

## 1. Start local MQTT broker

From the PointCloudTT repository root:

```bash
cd apps/mygardenos
docker compose up -d mqtt
```

The broker listens on port `1883`.

## 2. Find the Mac LAN IP

On this machine, the current LAN IP is:

```text
192.168.68.181
```

If the network changes, run:

```bash
ifconfig | grep "inet "
```

Use the non-`127.0.0.1` address.

## 3. Configure the robot over Bluetooth

BLE connection details confirmed by the robot vendor:

```text
Scan name: NBMower
Service UUID: fff0
Read/notify UUID: fff1
Write UUID: fff2
```

Use the robot `$AT` command:

```json
{"command":"$AT,1,10,192.168.68.181,1883,admin,admin"}\r\n
```

For this local broker, `admin/admin` is only a placeholder because anonymous access is enabled.

## 4. Watch robot reports

Subscribe to heartbeat:

```bash
docker run --rm --network host eclipse-mosquitto:2 mosquitto_sub -h 127.0.0.1 -p 1883 -t HeartBeat -v
```

If Docker host networking is unavailable, use:

```bash
cd apps/mygardenos
docker compose exec mqtt mosquitto_sub -h 127.0.0.1 -p 1883 -t HeartBeat -v
```

## 5. Send a test command

Replace `C8782C1A399F` with the robot `robotId`.

```bash
cd apps/mygardenos
docker compose exec mqtt mosquitto_pub -h 127.0.0.1 -p 1883 -t RobotCommand/C8782C1A399F -m '{"commandCode":"local-001","robotId":"C8782C1A399F","command":"$STATUS"}'
```

Then watch `ResponseCommand`:

```bash
cd apps/mygardenos
docker compose exec mqtt mosquitto_sub -h 127.0.0.1 -p 1883 -t ResponseCommand -v
```
