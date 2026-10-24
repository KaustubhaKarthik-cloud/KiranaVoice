import soundfile as sf, numpy as np
from kokoro import KPipeline
p=KPipeline(lang_code="h",repo_id="hexgrad/Kokoro-82M")
T={"a1":"नमस्ते! शर्मा किराना से बोल रहे हैं। बताइए, क्या भेजना है?",
"a2":"ठीक है, दो किलो आटा, एक लीटर फॉर्च्यून ऑयल, छह अंडे। सही है?",
"a3":"डन, बारह अंडे। और कुछ?",
"a4":"शुक्रिया रमेश जी! ऑर्डर नोट हो गया, थोड़ी देर में भेज देंगे।"}
for v in ["hf_alpha","hf_beta","hm_omega","hm_psi"]:
  for k,t in T.items():
    a=np.concatenate([r.audio.numpy() for r in p(t,voice=v,speed=1.05)]); sf.write(f"{k}_{v}.wav",a,24000)
print("ok")
