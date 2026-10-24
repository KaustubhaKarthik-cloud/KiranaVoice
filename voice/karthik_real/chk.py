import json,glob,os
from faster_whisper import WhisperModel
m=WhisperModel("medium",device="cpu",compute_type="int8")
for l in "n1 n2 n3 n4 n5 c1 c2".split():
  s,_=m.transcribe(f"karthik_real/cut/{l}.wav",word_timestamps=True,language="en",initial_prompt="KiranaVoice, Gnani Prisma, Gnani Timbre, Hinglish. Bhaiya, atta, Fortune oil, ande bhej do.")
  ws=[(w.word.strip(),round(w.start,2),round(w.end,2)) for x in s for w in x.words]
  print(l,' '.join(w[0] for w in ws)); json.dump(ws,open(f"karthik_real/cut/{l}.words.json","w"))
for f in sorted(glob.glob("agent_hi/a[23][xy]_*.wav")):
  s,_=m.transcribe(f,language="hi"); print(os.path.basename(f),''.join(x.text for x in s))
