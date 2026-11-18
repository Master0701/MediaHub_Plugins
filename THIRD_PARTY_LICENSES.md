# Third-Party Licenses

This file documents third-party software referenced by plugins in the
`MediaHub_Plugins` repository.

First-party MediaHub plugins are proprietary unless explicitly stated
otherwise. Third-party components retain their own licenses.

## ReNamer

- **Product:** ReNamer
- **Vendor:** Furious Technologies Limited / den4b
- **Used by:** MediaHub Smart Renamer
- **Usage:** Optional external Windows backend
- **Bundled in this repository:** No
- **Installation:** Managed separately by the MediaHub Tool Manager
- **Homepage:** https://www.den4b.com/products/renamer
- **Portable download:** https://www.den4b.com/download/renamer/portable
- **License:** ReNamer Lite: CC BY-NC-ND 3.0 / non-commercial use; a Pro license is required for commercial use according to the vendor terms.
- **Vendor license information:** https://www.den4b.com/license

No ReNamer binaries are stored in this repository.

## AI-Node Test Provider

The AI-Node test provider declares its own project license as `MIT` in its
`plugin.json`.

It is intentionally not rewritten to the proprietary first-party MediaHub
plugin license.

## SmolVLM2 Vision

### MediaHub plugin

- **Plugin:** MediaHub SmolVLM2 Vision
- **Plugin ID:** `mediahub.smolvlm2`
- **Plugin license:** MIT
- **Targets:** Raspberry Pi AI Node and Windows Compute Node
- **Model files bundled in plugin:** No
- **Third-party runtime bundled in plugin:** No

The MIT license applies to the MediaHub SmolVLM2 plugin implementation.
It does not replace or modify the licenses of the model, runtime libraries,
CUDA components, or other third-party software.

### SmolVLM2 model

- **Model:** `HuggingFaceTB/SmolVLM2-500M-Video-Instruct`
- **Provider:** Hugging Face / HuggingFaceTB
- **License:** Apache-2.0
- **Bundled in this repository:** No
- **Bundled in `.mhaiplugin`:** No
- **Storage/installation:** Managed separately through MediaHub Tools/runtime management
- **Model page:** https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct

The concrete model revision and its accompanying license information must be
preserved by the MediaHub model/tool management when the model is downloaded,
cached, installed, packaged, exported, or redistributed.

### Runtime dependencies

The tested Windows Compute Node runtime currently uses:

| Component | Tested version | License / license metadata |
|---|---:|---|
| PyTorch | 2.14.0+cu126 | Apache-2.0 plus bundled third-party licenses |
| torchvision | 0.29.0+cu126 | BSD |
| Transformers | 5.17.0 | Apache-2.0 |
| Accelerate | 1.15.0 | Apache |
| Safetensors | 0.8.0 | Apache |
| Hugging Face Hub | 1.33.0 | Apache-2.0 |
| Pillow | 12.3.0 | MIT-CMU |
| num2words | 0.5.14 | LGPL |
| NumPy | 2.5.3 | BSD-3-Clause plus bundled third-party licenses |

These runtime packages are not stored in the MediaHub SmolVLM2 plugin package.
Their upstream license files remain part of their respective runtime
installations and must be preserved.

Platform-specific accelerator components, including NVIDIA CUDA components,
retain their respective vendor licenses and terms.

See also:

`ai_node_plugins/smolvlm2/THIRD_PARTY_NOTICES.md`

## MediaHub Interaktions-KI (`ai_node_plugins/interaktions_ki`)

| Fremdkomponente | Zweck | Lizenz-/Verteilhinweis |
|---|---|---|
| llama.cpp / llama-server | lokale GGUF-Chat-Inferenz | MIT; Original-Lizenz und Notices des tatsächlich verwendeten Builds beachten |
| GGUF-Sprachmodell | Chat-Modell | Modellabhängige Lizenz und Nutzungsbedingungen; Herkunft vor Installation prüfen; nicht im Plugin enthalten |
| NVIDIA CUDA | optionale GPU-Beschleunigung | separate NVIDIA-Lizenzbedingungen; abhängig vom gewählten Binary-Paket |

Das Plugin bündelt laut Manifest keine Modelle und installiert keine Fremdsoftware stillschweigend. Vor Veröffentlichung die tatsächlich in den `.mhaiplugin`-Paketen und Runtime-Archiven enthaltenen Dateien und deren Original-Lizenztexte prüfen. Die vollständige Lizenzverwaltung für Windows-Node-Laufzeitkomponenten liegt zusätzlich im Repository `MediaHub-AI-Node`.

## Interaktions-KI v0.1.12 (Windows Compute Node)

Das optionale Plugin nutzt eine separat installierte llama.cpp-Runtime (MIT, https://github.com/ggml-org/llama.cpp). GGUF-Modelle unterliegen ihren jeweiligen Modelllizenzen. NVIDIA/CUDA-Komponenten haben gesonderte Herstellerbedingungen. Vor einem Release sind die tatsächlich ausgelieferten Runtime-Binärdateien, deren Lizenztexte und etwaige Drittanbieterhinweise zu prüfen. Modelle und Runtime werden nicht pauschal als MIT-lizenziert eingestuft.
