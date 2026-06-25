export const demoEmail = "planning-demo@example.com";
export const demoPassword = "Planning123";
export const robotId = "SIM-MOWER-001";

export const workZone = [
  { x: 0, y: 0, lat: -36.8485, lng: 174.7633 },
  { x: 14, y: 0 },
  { x: 14, y: 9 },
  { x: 0, y: 9 },
];

export const noGoZone = [
  { x: 5.2, y: 3 },
  { x: 7.2, y: 3 },
  { x: 7.2, y: 5 },
  { x: 5.2, y: 5 },
];

export const dockPosition = { x: 1, y: 1 };

export const flowSteps = [
  "Login",
  "Property",
  "Map",
  "Zones",
  "Dock",
  "Path",
  "Task",
  "Confirm",
  "Dispatch",
  "Heartbeat",
  "RTK pause",
];
