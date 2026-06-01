# PointCloudTT Product Requirements

## 1. Project Goal

PointCloudTT converts high-precision handheld scan point clouds into editable 2D floor maps.

The 2D map should allow users to:

- Adjust the outer boundary.
- Mark no-go zones.
- Mark corridors or passages.
- Add future annotation types without redesigning the editor.
- Export a structured map file for downstream systems.

The first product version should be a semi-automatic workflow. Automatic detection can assist the user, but the user must be able to correct the result manually.

## 2. Target Workflow

1. User imports a point cloud file.
2. System shows a 3D preview of the point cloud.
3. System generates a 2D top-down map candidate.
4. User adjusts the map boundary.
5. User marks no-go zones.
6. User marks corridors.
7. User validates the map.
8. User exports the map as structured data.
9. User can later import the map and continue editing.

## 3. MVP Scope

The MVP should prove the whole pipeline with the smallest useful feature set:

- Import at least one common point cloud format.
- Preview point cloud metadata and visual shape.
- Generate a 2D projection from the point cloud.
- Draw and edit one outer boundary.
- Draw and edit multiple no-go zones.
- Draw and edit multiple corridors.
- Export a versioned JSON map file.
- Reopen an exported map for continued editing.

## 4. Non-MVP Scope

These are important but should not block the first usable version:

- Fully automatic boundary recognition.
- Complex obstacle classification.
- Multi-floor or multi-level maps.
- Real-time scan streaming.
- Direct physical device control.
- Cloud collaboration.
- User accounts.
- Permission management.

## 5. Core Concepts

### Point Cloud

The raw 3D scan data from a handheld scanner. It may contain ground, walls, plants, people, scanner noise, and temporary objects.

### 2D Base Map

A top-down projection or raster/vector representation generated from the point cloud. It is used as the visual reference layer for editing.

### Boundary

The outer valid area of the map. Downstream systems should treat the area outside this boundary as invalid.

### Annotation

A semantic object placed on the map. Examples include no-go zones, corridors, work areas, charging zones, obstacles, or temporary blocked areas.

### No-Go Zone

An area inside the boundary that should be excluded from normal traversal or work.

### Corridor

A passage or allowed route area. Depending on downstream needs, it may be represented as a polygon, a centerline with width, or a directed path.

## 6. User Stories

### Import and Preview

As a user, I want to import a handheld scanner point cloud so that I can start converting it into a 2D map.

Acceptance criteria:

- The app accepts at least one supported point cloud format.
- The app shows file metadata such as point count and bounding box.
- The app can display a basic 3D preview.
- Invalid or unsupported files produce a clear error.

### Generate 2D Map

As a user, I want the system to generate a 2D top-down map from the point cloud so that I do not need to draw everything from scratch.

Acceptance criteria:

- The app generates a visible 2D projection.
- The projection keeps real-world proportions.
- The projection has a stable coordinate system.
- The user can see the relation between the point cloud and the 2D map.

### Edit Boundary

As a user, I want to adjust the outer boundary so that the map matches the real usable area.

Acceptance criteria:

- The user can create a polygon boundary.
- The user can drag boundary points.
- The user can add and remove points.
- The boundary cannot silently become invalid.

### Mark No-Go Zones

As a user, I want to mark no-go zones so that unsafe or restricted areas are excluded.

Acceptance criteria:

- The user can create multiple no-go zones.
- Each no-go zone can be edited and deleted.
- No-go zones are stored as annotation objects.
- The app warns if a no-go zone is outside the boundary.

### Mark Corridors

As a user, I want to mark corridors so that narrow passable areas can be represented explicitly.

Acceptance criteria:

- The user can create multiple corridors.
- The corridor representation is explicit in the exported data.
- The first version may use polygons.
- A later version may support centerlines with width and direction.

### Export Map

As a user, I want to export the edited map so that another system can consume it.

Acceptance criteria:

- The export format is JSON.
- The export includes schema version, coordinate system, boundary, and annotations.
- The export is deterministic for the same map state.
- The exported file can be imported again.

## 7. Technical Requirements

### Point Cloud Processing

- Support a modular import layer.
- Preserve source file metadata.
- Support downsampling for large files.
- Generate a top-down 2D projection.
- Keep a clear mapping between world coordinates and screen coordinates.

### Editor

- Provide pan and zoom.
- Provide point, polygon, and line editing primitives.
- Provide undo and redo.
- Provide layer visibility controls.
- Keep editing state separate from exported map schema.

### Annotation System

- Use typed annotations.
- Store geometry and properties separately.
- Allow future annotation types without changing the core map container.
- Validate annotations based on type-specific rules.

### Validation

The app should detect or warn about:

- Boundary self-intersection.
- Empty boundary.
- Annotation outside the boundary.
- No-go zones overlapping in unexpected ways.
- Corridor geometry that cannot be interpreted.
- Missing coordinate system metadata.

## 8. Recommended Model Routing

Use the smallest sufficient model for each task:

- GPT 5.4 mini: UI copy, style, icon, simple panel tweaks.
- GPT 5.2: simple explanations, small documentation edits, very low-risk local changes.
- GPT 5.3Codex: normal implementation in one known module.
- GPT 5.4: cross-module integration, point-cloud projection, schema and validation logic.
- GPT 5.5: architecture decisions, safety semantics, direct device-control implications, complex automatic recognition.

## 9. Main Risks

1. Point cloud noise may make automatic boundary extraction unreliable.
2. A 2D projection may lose important height information.
3. Coordinate system mistakes can make the exported map unsafe or unusable.
4. Annotation types may grow beyond the initial design.
5. If the map is later used by a physical device, validation and safety semantics become high risk.

## 10. First Milestone

The first milestone is a local prototype that can:

1. Load one supported point cloud file.
2. Show a basic 3D preview.
3. Generate a 2D projection.
4. Let the user draw boundary, no-go zones, and corridors.
5. Export a versioned JSON map.

