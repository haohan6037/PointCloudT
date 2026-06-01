# PointCloudTT Agent Task Breakdown

## 1. Purpose

This file breaks PointCloudTT into small, assignable tasks for future sub-agents.

Use this as the baseline when delegating work. Each task includes difficulty, recommended model, scope, and expected output.

## 2. Model Routing

Available models:

- GPT5.5
- GPT 5.4
- GPT5.4 mini
- GPT 5.3Codex
- GPT 5.2

Recommended use:

- GPT5.5: architecture, safety-critical map semantics, complex recognition, physical-device implications.
- GPT 5.4: cross-module design, point-cloud processing, coordinate systems, validation.
- GPT 5.3Codex: normal implementation tasks in known modules.
- GPT5.4 mini: small UI polish, copy, CSS, icons, simple panels.
- GPT 5.2: simple documentation, issue cleanup, small low-risk edits.

## 3. Task Levels

- Tier A: small local task, low risk.
- Tier B: normal implementation task, one known module or feature.
- Tier C: cross-module integration or difficult algorithm.
- Tier D: architecture or safety-critical design.

## 4. Work Packages

### WP-00: Project Baseline Docs

Task level: Tier B
Recommended model: GPT 5.2 or GPT 5.3Codex
Risk: low
Scope:

- Keep `docs/PRD.md` current.
- Keep `docs/MAP_SCHEMA.md` current.
- Keep `docs/AGENT_TASKS.md` current.

Expected output:

- Updated documentation with clear assumptions and acceptance criteria.

### WP-01: Point Cloud File Import

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Choose initial supported format.
- Implement file loading.
- Extract point count, bounds, and metadata.
- Return useful errors for unsupported files.

Expected output:

- Import module.
- One sample file loading path.
- Basic tests or manual verification notes.

### WP-02: 3D Point Cloud Preview

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Render imported point cloud.
- Support camera pan, zoom, and rotate.
- Show basic metadata.
- Handle large files with downsampling.

Expected output:

- Usable 3D preview.
- Clear performance limits.

### WP-03: Downsampling and Preprocessing

Task level: Tier C
Recommended model: GPT 5.4
Risk: medium
Scope:

- Reduce point count while preserving map-relevant shape.
- Remove obvious outliers.
- Keep original source metadata.
- Make preprocessing deterministic where possible.

Expected output:

- Preprocessing pipeline.
- Tunable parameters.
- Before and after metrics.

### WP-04: Ground Plane and Orientation Detection

Task level: Tier C
Recommended model: GPT 5.4
Risk: high
Scope:

- Detect the dominant ground or map plane.
- Estimate orientation.
- Decide how to handle tilted scans.
- Document assumptions.

Expected output:

- Plane detection method.
- Failure cases.
- Manual override path if detection is wrong.

### WP-05: 2D Projection Generation

Task level: Tier C
Recommended model: GPT 5.4
Risk: high
Scope:

- Project relevant 3D points into 2D map coordinates.
- Preserve real-world scale.
- Generate a visual base layer.
- Store transform metadata.

Expected output:

- 2D projection pipeline.
- Coordinate transform.
- Visual base map layer.

### WP-06: Initial Boundary Candidate

Task level: Tier C
Recommended model: GPT 5.4
Risk: high
Scope:

- Generate a rough boundary candidate from projected points.
- Use density, hull, alpha shape, or similar methods.
- Allow manual correction.

Expected output:

- Candidate polygon.
- Confidence or warning when result is unreliable.
- Manual edit fallback.

### WP-07: 2D Map Editor MVP

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Canvas or SVG based editor.
- Pan and zoom.
- Polygon drawing.
- Point dragging.
- Add and remove points.
- Selection and deletion.

Expected output:

- User can draw and edit boundary and annotation polygons.

### WP-08: Boundary Editing

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Create one main boundary.
- Edit boundary points.
- Prevent or warn about invalid boundary states.

Expected output:

- Boundary tool.
- Boundary validation messages.

### WP-09: No-Go Zone Editing

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Create multiple no-go zones.
- Edit zone points.
- Delete zones.
- Store zones as annotations.

Expected output:

- No-go zone tool.
- Export-compatible annotation data.

### WP-10: Corridor Editing

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Create corridor annotations.
- MVP may represent corridors as polygons.
- Prepare schema for future line-plus-width representation.

Expected output:

- Corridor tool.
- Corridor annotation export.

### WP-11: Annotation Type Registry

Task level: Tier C
Recommended model: GPT 5.4
Risk: medium
Scope:

- Define annotation type metadata.
- Support allowed geometry types.
- Support default properties.
- Support type-specific styles.
- Avoid hard-coding every type into editor internals.

Expected output:

- Extensible annotation registration pattern.
- Initial definitions for `no_go_zone` and `corridor`.

### WP-12: Map Import and Export

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Export map JSON.
- Import exported map JSON.
- Preserve schema version.
- Preserve unknown safe properties where possible.

Expected output:

- Round-trip import/export flow.
- Example map file.

### WP-13: Validation Engine

Task level: Tier C
Recommended model: GPT 5.4
Risk: high
Scope:

- Validate boundary.
- Validate annotations.
- Detect self-intersections.
- Detect outside-boundary annotations.
- Provide human-readable errors.

Expected output:

- Validation module.
- Validation result structure.
- Targeted tests.

### WP-14: UI Panels and Layer Controls

Task level: Tier A
Recommended model: GPT5.4 mini
Risk: low
Scope:

- Toolbar.
- Layer list.
- Object properties panel.
- Visibility toggles.
- Delete and rename controls.

Expected output:

- Usable editing interface around the map canvas.

### WP-15: Visual Design Polish

Task level: Tier A
Recommended model: GPT5.4 mini
Risk: low
Scope:

- Icons.
- Button states.
- Selection handles.
- Color palette.
- Empty states and error states.

Expected output:

- Clear and professional map-editing UI.

### WP-16: Safety Semantics for Device Use

Task level: Tier D
Recommended model: GPT5.5
Risk: high
Scope:

- Define what boundary, no-go zone, and corridor mean for a physical device.
- Define whether corridors are preferred, required, or merely annotated.
- Define behavior when geometry is invalid or missing.
- Define fail-safe behavior for downstream systems.

Expected output:

- Safety semantics design doc.
- Explicit non-goals.
- Test scenarios for unsafe maps.

### WP-17: Automatic Recognition Improvements

Task level: Tier D
Recommended model: GPT5.5
Risk: high
Scope:

- Improve automatic boundary extraction.
- Detect obstacles or restricted areas from point cloud features.
- Compare multiple algorithms.
- Build confidence scoring.

Expected output:

- Algorithm comparison.
- Improved extraction prototype.
- Known failure cases.

### WP-18: Sample Data and Acceptance Tests

Task level: Tier B
Recommended model: GPT 5.3Codex
Risk: medium
Scope:

- Add sample point clouds or documented sample placeholders.
- Add expected exported map fixtures.
- Add manual test checklist.

Expected output:

- Repeatable verification path.
- Example files for future agents.

## 5. Suggested Execution Order

1. WP-00: Project Baseline Docs
2. WP-01: Point Cloud File Import
3. WP-02: 3D Point Cloud Preview
4. WP-05: 2D Projection Generation
5. WP-07: 2D Map Editor MVP
6. WP-08: Boundary Editing
7. WP-09: No-Go Zone Editing
8. WP-10: Corridor Editing
9. WP-12: Map Import and Export
10. WP-13: Validation Engine
11. WP-11: Annotation Type Registry
12. WP-03 and WP-04: Better preprocessing and plane detection
13. WP-06: Initial boundary candidate
14. WP-14 and WP-15: UI panels and visual polish
15. WP-16: Safety semantics, before any physical-device integration
16. WP-17: Automatic recognition improvements
17. WP-18: Acceptance sample set

## 6. Sub-Agent Rules

When assigning sub-agents:

- Give each sub-agent exactly one work package unless the packages are tightly coupled.
- Do not assign two agents to edit the same files.
- Keep architecture decisions in the main session or GPT5.5.
- Ask agents to report changed files, assumptions, verification, and rollback notes.
- Review sub-agent output before merging it into the main project.

## 7. First Recommended Sub-Agent Batch

Batch 1 should avoid high-risk automatic recognition and focus on a working pipeline:

1. Requirements Agent
   - Work package: WP-00
   - Model: GPT 5.2 or GPT 5.3Codex

2. Point Cloud Import Agent
   - Work package: WP-01
   - Model: GPT 5.3Codex

3. 2D Editor Agent
   - Work packages: WP-07, WP-08, WP-09, WP-10
   - Model: GPT 5.3Codex

4. Schema Agent
   - Work packages: WP-11, WP-12
   - Model: GPT 5.4

5. Validation Agent
   - Work package: WP-13
   - Model: GPT 5.4

## 8. Stop Conditions

Pause and return to the main session if:

- A task requires changing more than 3 files beyond the assigned scope.
- The point cloud coordinate system is unclear.
- Exported map semantics affect real device movement.
- Validation rules conflict with user expectations.
- The chosen file format cannot represent required data safely.

