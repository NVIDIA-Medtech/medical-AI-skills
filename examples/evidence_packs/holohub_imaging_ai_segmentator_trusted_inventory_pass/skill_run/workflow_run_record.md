# Workflow Run Record

- run id: 37c9c99717ca
- skill: holohub_imaging_ai_segmentator v0.1.0
- started: 2026-05-26T03:09:58.603416+00:00
- finished: 2026-05-26T03:10:21.712118+00:00
- elapsed: 23.109s
- exit code: 0

## Skill
- dir: skills/holohub-imaging-ai-segmentator
- entrypoint: scripts/run_holohub_app.py

## Fixture
- path: .workbench_data/holohub_input/spleen_10
- sha256: 34e824615d7ab5aa48029ac53c4cebb0130645785dfb5a4bba1aacf457bf96ea
- size: 28903998 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "invocation": {
    "holohub_root": "<repo>/.workbench_data/holohub",
    "holohub_commit": "90e0af6b2fa938d2bfa93237d177c76e4763158a",
    "mode": "container",
    "command": [
      "./holohub",
      "run",
      "imaging_ai_segmentator",
      "--configure-args=-DHOLOHUB_DOWNLOAD_DATASETS=OFF"
    ],
    "exit_code": 0,
    "container_image": "holohub-imaging_ai_segmentator:main",
    "container_image_id": "sha256:eaa9134939e2c088c002c9f8b21996891baf5b732c43fa692dd06bfb741c48fe",
    "container_provenance": {
      "image_ref": "holohub-imaging_ai_segmentator:main",
      "inspect": {
        "status": "ok",
        "id": "sha256:eaa9134939e2c088c002c9f8b21996891baf5b732c43fa692dd06bfb741c48fe",
        "repo_tags": [
          "holohub-imaging_ai_segmentator:90e0af6b2fa9",
          "holohub-imaging_ai_segmentator:main",
          "holohub:imaging_ai_segmentator"
        ],
        "labels": {
          "com.nvidia.build.id": "280215355",
          "com.nvidia.build.ref": "dc058d9a75f3d1a699daef7e45a3c946bd06e321",
          "com.nvidia.cublas.version": "13.3.0.5",
          "com.nvidia.cublasmp.version": "0.8.0.2023",
          "com.nvidia.cuda.version": "9.0",
          "com.nvidia.cudla.version": "13.2.51",
          "com.nvidia.cudnn.version": "9.20.0.48",
          "com.nvidia.cufft.version": "12.2.0.37",
          "com.nvidia.curand.version": "10.4.2.51",
          "com.nvidia.cusolver.version": "12.1.0.51",
          "com.nvidia
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.