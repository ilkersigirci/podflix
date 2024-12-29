I want to create an application that does the following:

- Take the user podcast mp3 file from chainlit ui
- Transcribe the podcast mp3 file to text by calling openai whisper remote api
- Show the transcribed text to the user in the chainlit ui
- Allow the user the ability to chat the transcribed text using langchain
- Langchain implementation is a langgraph graph with RAG model, and the LLM model is remote openai api
