# PPT File Generation Video Support Design

**Goal:** Allow the existing PPT `file-generation` flow to accept video files as source material, reuse the current reference-file parsing pipeline, and present honest frontend guidance about the quality limits of video understanding.

## Scope

This design only extends the current `file-generation` mode. It does not introduce a new creation mode, a dedicated video task type, or a separate video-specific generation workflow.

## Current State

- The frontend `file-generation` mode only allows `pdf/doc/docx`.
- The backend `file-generation` route also rejects any non-`pdf/doc/docx` upload.
- The project already has a working video parsing stack through `ParserFactory -> VideoParser`.
- The `dialog` mode already supports uploading video as a reference file, proving the parser integration path exists.

## Proposed Approach

Extend the existing `file-generation` pipeline instead of creating a parallel video feature:

- Accept video extensions in the `file-generation` route.
- Keep storing the uploaded file as a `PPTReferenceFile` and dispatch the existing `file_generation_task`.
- Let `file_generation_task` continue calling `_parse_reference_file_content`, which already delegates to `ParserFactory`, including `VideoParser`.
- Update the frontend upload affordances so users can select video files in `file-generation` mode.
- Add explicit copy explaining that video parsing quality depends on multimodal and ASR configuration, and may fall back to coarse keyframe-based extraction.

This keeps the architecture small, preserves existing async behavior, and avoids inventing a second source ingestion system.

## Backend Changes

### Route validation

Update `POST /api/v1/ppt/projects/file-generation` to allow:

- documents: `pdf`, `doc`, `docx`
- videos: `mp4`, `mov`, `avi`, `mkv`, `flv`

### MIME normalization

Extend `_normalize_file_ext` so common video MIME types map cleanly when the filename is incomplete or unreliable.

### Task pipeline

No new task type is needed. The current `file_generation_task` already supports parsing arbitrary supported reference files through `_parse_reference_file_content`.

## Frontend Changes

### Upload affordance

Update `teacher-platform/src/views/ppt/PptHome.vue` so `file` mode accepts the same video extensions as the backend.

### User guidance

Adjust file-mode description and upload hint text to:

- advertise video support
- explain that without full multimodal configuration, video extraction may degrade to partial keyframe-based understanding

This is intentionally static guidance. It avoids introducing a new backend capability probe just to show environment-dependent messaging.

## Testing

### Backend

- Add a route test showing `mp4` upload is now accepted by `file-generation`.
- Keep an unsupported-type rejection test, but switch it to a genuinely unsupported format like `xlsx`.

### Frontend

The change is UI-only and localized to accept/hint strings, so no new frontend test is required for this pass.

## Risks

- Video support may still be low-quality in environments missing API keys for multimodal summarization or ASR.
- Large videos may remain slow because parsing is still async and model-dependent.

These are acceptable for this iteration because the goal is to make the feature available through the existing pipeline, not to guarantee premium-quality video understanding in every deployment.
