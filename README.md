<p align="center">
  <img width="600" src="https://raw.githubusercontent.com/ilkersigirci/podflix/main/configs/chainlit/public/banner.png">
</p style = "margin-bottom: 2rem;">

[![Lint status](https://img.shields.io/github/actions/workflow/status/ilkersigirci/podflix/lint.yml?branch=main)](https://github.com/ilkersigirci/podflix/actions/workflows/lint.yml?query=branch%3Amain)
[![Supported Python versions](https://img.shields.io/badge/python-3.11_%7C_3.12_%7C_3.13-blue?labelColor=grey&color=blue)](https://github.com/ilkersigirci/podflix/blob/main/pyproject.toml)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://ilkersigirci.github.io/podflix/)
[![License](https://img.shields.io/github/license/ilkersigirci/podflix)](https://img.shields.io/github/license/ilkersigirci/podflix)

## Description

- Langfuse credentials:
    - email: podflix@mail.com
    - password: podflix123

- Chainlit credentials:
    - username: admin
    - password: admin

- To change db backend from postgresql to sqlite: Change in `.env` file `ENABLE_SQLITE_DATA_LAYER=true`

## Cloning the Repository

To clone this repository including all submodules, use:

```bash
git clone --recurse-submodules https://github.com/yourusername/podflix.git
```

## Update Submodules

```bash
make update-submodules
```

## Healthchecks

- Assuming `DOMAIN_NAME=localhost`

### Openai like model api

- Request with system message assuming `MODEL_NAME=qwen2-0_5b-instruct-fp16.gguf`

```bash
curl --request POST \
    --url https://llamacpp.localhost/v1/chat/completions \
    --header "Content-Type: application/json" \
    --data '{
  "model": "qwen2-0_5b-instruct-fp16.gguf",
  "messages": [
  {
      "role": "system",
      "content": "You are a helpful virtual assistant trained by OpenAI."
  },
  {
    "role": "user",
    "content": "Who are you?"
  }
  ],
  "temperature": 0.8,
  "stream": false
}'
```
- Request without system message assuming `MODEL_NAME=qwen2-0_5b-instruct-fp16.gguf`

```bash
curl --request POST \
 --url https://llamacpp.localhost/v1/chat/completions \
    --header "Content-Type: application/json" \
    --data '{
  "model": "qwen2-0_5b-instruct-fp16.gguf",
  "messages": [
  {
    "role": "user",
    "content": "Who are you?"
  }
  ],
  "temperature": 0.8,
  "stream": false
}'
```
