# MyGardenOS MQTT broker

This folder contains the Mosquitto MQTT broker used for robot telemetry tests.

## Railway deployment

Create a separate Railway service from this same GitHub repository and set:

```text
Root Directory: mqtt
Builder: Dockerfile
Target Port: 1883
Public Networking: TCP Proxy
```

After Railway creates the TCP proxy, configure the robot with:

```json
{"command":"$AT,1,10,nozomi.proxy.rlwy.net,53239,admin,admin"}\r\n
```

Replace the host and port with the current Railway TCP proxy values if they change.

For the backend subscriber, set these Railway variables on the backend service:

```text
MQTT_HOST=nozomi.proxy.rlwy.net
MQTT_PORT=53239
```

The current broker allows anonymous MQTT connections for first-device bring-up. Add authentication before production use.
