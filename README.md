# Podflix

Chat with your podcast

- Langfuse credentials:
    - email: podflix@mail.com
    - password: podflix123

- Chainlit credentials:
    - username: admin
    - password: admin

- To change db backend from sqlite to postgresql: Change the DATABASES configuration `.env` file

```bash
SQLALCHEMY_DB_TYPE=postgres
POSTGRES_DB=your_db_name
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5432
POSTGRES_USER=your_username
```

## Healthchecks

### vllm

- Request with system message assuming `MODEL_NAME=qwen2-0_5b-instruct-fp16.gguf`

```bash
curl --request POST \
    --url http://0.0.0.0:8000/v1/chat/completions \
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
 --url http://0.0.0.0:8000/v1/chat/completions \
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
