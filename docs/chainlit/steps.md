# Custom Audio Element Implementation

To implement the custom audio element with transcript display, follow these steps:

1. Create a new file `public/elements/AudioWithTranscript.jsx`:
   - Add an audio player component at the top
   - Add a scrollable transcript area below
   - Use Shadcn components for consistent styling

2. Update the audio.py file:
   - After transcription, create a new CustomElement
   - Pass the audio URL and transcript as props
   - Add the element to the system message

3. Example usage in audio.py:
```python
audio_element = cl.CustomElement(
    name="AudioWithTranscript",
    props={
        "audioUrl": file.url,
        "transcript": audio_text
    }
)
message.elements.append(audio_element)
```

The element will display the audio player at the top with playback controls and show the transcript in a scrollable area below it.
