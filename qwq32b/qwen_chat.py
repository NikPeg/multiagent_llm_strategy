from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
MODEL_ID = "Qwen/Qwen1.5-32B"
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",
    trust_remote_code=True,
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)


print("Загрузка токенизатора и модели... (это может занять несколько минут)")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map="auto",
    trust_remote_code=True,
    load_in_4bit=True  # Или load_in_8bit=True, если памяти достаточно
)

# Инструкции модели — просим всегда отвечать по-русски
system_prompt = (
    "You are a helpful assistant who always answers in English. "
)

print(
    "Готово! Пиши свои вопросы (на русском или английском).\n"
    "Для выхода напиши: ВЫХОД"
)

history = []

while True:
    user_input = input("\nТы: ")
    if user_input.strip().lower() in ['выход', 'exit', 'quit']:
        print("Пока!")
        break

    history.append({"role": "user", "content": user_input})
    prompt = system_prompt
    for turn in history:
        if turn["role"] == "user":
            prompt += f"User: {turn['content']}\n"
        else:
            prompt += f"Assistant: {turn['content']}\n"
    prompt += "Assistant:"

    # Токенизация и генерация
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output_tokens = model.generate(
        **inputs,
        max_new_tokens=256,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=True
    )
    answer = tokenizer.decode(
        output_tokens[0][inputs['input_ids'].shape[-1]:],
        skip_special_tokens=True
    ).strip()

    print(f"\nАссистент: {answer}")
    history.append({"role": "assistant", "content": answer})

