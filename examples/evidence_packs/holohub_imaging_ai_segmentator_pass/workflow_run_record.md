# Workflow Run Record

- run id: 62bde3a868ee
- skill: holohub_imaging_ai_segmentator v0.1.0
- started: 2026-05-10T08:16:20.513102+00:00
- finished: 2026-05-10T08:16:30.008868+00:00
- elapsed: 9.496s
- exit code: 0

## Skill
- dir: skills/holohub-imaging-ai-segmentator
- entrypoint: scripts/run_holohub_app.py

## Fixture
- path: .workbench_data/holohub_input/spleen_10
- sha256: 1b6cc0633a91ab31b8938d1c585afb186556a15f96dfdd4dcca577ee1cc4b937
- size: 28903998 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- integrity: clean

## Output (excerpt)
```json
{
  "invocation": {
    "holohub_root": ".workbench_data/holohub",
    "holohub_commit": "0eb7dcfb94d8b09a28075fb87337fcc12cff0af5",
    "mode": "container",
    "command": [
      "./holohub",
      "run",
      "imaging_ai_segmentator",
      "--configure-args=-DHOLOHUB_DOWNLOAD_DATASETS=OFF"
    ],
    "exit_code": 0,
    "container_image": "holohub-imaging_ai_segmentator:main",
    "container_image_id": "sha256:91ffc50991fa49704a4f04c6dade08322208311113de705d526c9489b31a5aa0",
    "input_path": ".workbench_data/holohub_input/spleen_10",
    "output_path": ".workbench_data/holohub/build/imaging_ai_segmentator/output",
    "model_path": null
  },
  "output": {
    "dicom_seg": {
      "count": 1,
      "total_bytes": 20213016,
      "files": [
        {
          "path": "1.2.826.0.1.3680043.10.511.3.81696044048617210694288790538523197.dcm",
          "bytes": 20213016,
          "sha256": "d30f812ae59059c29dc6632206637e84bc5363cf24eeed1a17b7065a7e89bcbc"
        }
      ]
    },
    "nifti": {
      "original": {
        "count": 1,
        "total_bytes": 57672032,
        "files": [
          {
            "path": "saved_images_folder/1.2.826.0.1.3680043.8.498/1.2.826.0.1.3680043.8.498.nii",
            "bytes": 57672032,
            "sha256": "b340f60fe3485a409878c3786188760addadf5f373a5fe2156380e38503a922c"
          }
        ]
      },
      "segmentati
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.