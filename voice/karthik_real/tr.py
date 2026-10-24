from faster_whisper import WhisperModel
m=WhisperModel("small",device="cpu",compute_type="int8")
s,_=m.transcribe("raw.wav",word_timestamps=True,language="en")
for x in s:
  print(f"{x.start:.2f}-{x.end:.2f} {x.text}")
  print("   ",[(w.word,round(w.start,2),round(w.end,2)) for w in x.words])
