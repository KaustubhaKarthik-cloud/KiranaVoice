import soundfile as sf, numpy as np
from kokoro import KPipeline
p=KPipeline(lang_code="h",repo_id="hexgrad/Kokoro-82M")
T={"a3x":"डन। बारह अंडे। और कुछ?","a3y":"हो गया, बारह अंडे। और कुछ?","a2x":"ठीक है, दो किलो आटा, एक लीटर फॉर्च्यून ऑयल, छः अंडे। सही है?"}
for v in ["hf_beta","hf_alpha"]:
  for sp in (1.0,1.1):
    for k,t in T.items():
      sf.write(f"{k}_{v}_{sp}.wav",np.concatenate([r.audio.numpy() for r in p(t,voice=v,speed=sp)]),24000)
