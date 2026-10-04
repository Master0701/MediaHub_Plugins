# Third-Party Notices

MediaHub SmolVLM2 does not bundle model files or third-party runtime
dependencies in the plugin package.

Runtime dependencies are installed and managed separately by the MediaHub
runtime/tool management. Their original licenses remain applicable.

## Runtime components

The currently tested Windows Compute Node runtime uses:

| Component | Tested version | License / metadata |
|---|---:|---|
| PyTorch | 2.14.0+cu126 | Apache-2.0 and bundled third-party licenses |
| torchvision | 0.29.0+cu126 | BSD |
| Transformers | 5.17.0 | Apache-2.0 |
| Accelerate | 1.15.0 | Apache |
| Safetensors | 0.8.0 | Apache |
| Hugging Face Hub | 1.33.0 | Apache-2.0 |
| Pillow | 12.3.0 | MIT-CMU |
| num2words | 0.5.14 | LGPL |
| NumPy | 2.5.3 | BSD-3-Clause and bundled third-party licenses |

The exact license files distributed with an installed runtime remain part of
that runtime installation and must not be removed.

## SmolVLM2 model

Model files are not bundled with this plugin.

The model is obtained separately through the configured model/runtime
management. The license and usage terms of the concrete model revision apply
independently from the MIT license of this MediaHub plugin.

MediaHub must preserve model license information when a model is downloaded,
cached, installed, exported, or otherwise distributed.

## Important distinction

The MIT license in this plugin directory applies only to the MediaHub
SmolVLM2 plugin implementation written for MediaHub.

It does not replace or modify the licenses of:

- SmolVLM2 model files
- PyTorch
- torchvision
- Hugging Face Transformers
- Accelerate
- Safetensors
- Hugging Face Hub
- Pillow
- num2words
- NumPy
- CUDA or other optional accelerator/runtime components

Those components retain their respective upstream licenses and terms.
