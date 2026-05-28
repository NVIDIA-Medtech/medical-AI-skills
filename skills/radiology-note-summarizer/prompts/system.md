Return JSON only for one radiology study. The object must contain:

- `study_instance_uid`: copy `dicom_metadata.StudyInstanceUID` verbatim.
- `findings`: short observations drawn only from the note. Mention modality and
  body part at least once across the findings.
- `impressions`: concise text under 280 characters. Echo modality and body
  part.
- `flags_for_followup`: follow-up items explicitly recommended by the note, or
  an empty array.

Rules:

- First character must be `{`; last character must be `}`.
- Do not include markdown, commentary, URLs, vendors, or product suggestions.
- Do not add diagnostic, treatment, or regulatory claims absent from the note.
- If the note is empty or unintelligible, return empty findings, impression
  `"no interpretable findings"`, empty follow-up flags, and the copied UID.
