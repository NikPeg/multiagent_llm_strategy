from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "Qwen/Qwen1.5-32B"

print("Загрузка токенизатора...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
print("Загрузка модели... (это может занять несколько минут и ~64ГБ места)")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",
    trust_remote_code=True,
    load_in_4bit=True  # Можно заменить на 8bit: load_in_8bit=True
)

prompt = "Привет! Расскажи коротко о преимуществах видеокарты NVIDIA A100."
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=128)
print("\nОтвет модели:\n")
print(tokenizer.decode(outputs[0], skip_special_tokens=True))

