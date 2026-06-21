# MQTT Vendor Integration Standard V1

## Purpose

This document defines the first GardenOS MQTT integration standard for vendor alignment.

Current priority:

- Keep the mowing service business flow independent from robot control.
- Use MQTT for robot/broker monitoring and later analysis.
- Preserve the manufacturer's existing topic behavior until a separate firmware/config plan is approved.
- Capture enough structure for future coverage, status, alerting, and service-quality analysis.

This standard is not a command-control safety design. The mowing platform must not publish robot movement commands from admin/customer/provider workflows until command identity, acknowledgement, timeout, retry, operator authority, audit logging, and emergency-stop behavior are designed and tested.

## Broker Configuration

Robot-facing settings must be provided as address/IP plus port.

Current AWS test broker:

```text
MQTT Address: 3.103.181.148
MQTT Port: 53239
```

Do not provide the HTTP application URL to the robot.

Credential, TLS, username, password, certificate, and firmware topic changes must be confirmed with the manufacturer before being enabled.

## Current Topics

The platform currently monitors:

```text
HeartBeat
ResponseCommand
$SYS/broker/log/#
```

The platform must not rename these topics or require the robot to publish different topics without a separate vendor change plan.

## Message Envelope

When the manufacturer can add or confirm structured JSON payloads, GardenOS expects this shape where possible:

```json
{
  "robotId": "string",
  "timestamp": "2026-06-22T10:20:30Z",
  "sequence": 12345,
  "messageType": "HeartBeat",
  "status": "idle | mowing | returning | charging | fault | offline",
  "batteryPercent": 87,
  "pose": {
    "x": 12.34,
    "y": 56.78,
    "heading": 1.57,
    "frame": "vendor-frame-name"
  },
  "accuracy": {
    "positionM": 0.5,
    "headingRad": 0.05
  },
  "error": {
    "code": "",
    "message": ""
  }
}
```

Minimum useful fields:

- `robotId`
- `timestamp`
- `messageType`
- `status`
- `sequence` or another monotonically increasing message id when available

## Coordinate Requirements

Vendor pose fields must not be treated as GardenOS map coordinates until confirmed.

Before coverage analysis, confirm:

- coordinate frame name
- origin
- x/y axis direction
- unit
- heading convention
- robot reference point
- timestamp source
- cut width
- working-state field
- position accuracy fields

GardenOS analysis will transform vendor coordinates into `GOS-MAP-XY`, defined in `docs/ROBOT_COORDINATE_ALIGNMENT_SPEC_V1.md`.

## Storage Rules

The mowing platform stores MQTT data in two layers:

- raw NDJSON archive for high-volume durable capture
- PostgreSQL `mqtt_messages` rows for searchable recent history and analysis metadata

PostgreSQL metadata should include:

- `topic`
- `payload`
- parsed JSON when valid
- `robot_id`
- `message_type`
- `source`
- `received_at`

Raw payloads may contain operational data but must not contain passwords, tokens, private keys, or customer secrets.

## Future Command Standard

Command publishing is out of scope for the current mowing platform business closure.

Before any command topic is enabled, define:

- command id
- actor id
- target robot id
- command type
- requested action
- created timestamp
- expiry timestamp
- safe duplicate handling
- acknowledgement states
- timeout behavior
- retry rules
- emergency-stop behavior
- audit log format

Acknowledgement states should distinguish:

- command sent
- command received
- command accepted
- action started
- action completed
- rejected
- failed
- timed out

## Vendor Questions

Ask the manufacturer to confirm:

1. Exact broker requirements: host/IP, port, TLS, username/password, certificate needs.
2. Exact publish topics and subscribe topics.
3. Payload format for `HeartBeat` and `ResponseCommand`.
4. Whether payloads are JSON, CSV, binary, or mixed.
5. Robot id field name and stability.
6. Timestamp format and timezone.
7. Status enum and fault/error codes.
8. Pose coordinate frame, units, axes, origin, and heading convention.
9. Whether sequence numbers or message ids exist.
10. Whether historical trajectory can be replayed or only live state is available.
11. Whether commands require acknowledgement and what responses look like.
12. Safety constraints for remote commands, especially movement and stop behavior.
