from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
quant_config = BitsAndBytesConfig(load_in_8bit=True)

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    quantization_config=quant_config
)

history = []

print("=== DeepSeek-R1-Distill-Qwen-32B Chat ===")
print("Для выхода напишите 'выход' или 'exit'.\n")

while True:
    user_input = input("Вы: ")
    if user_input.lower() in ['выход', 'exit']:
        print("Диалог завершён.")
        break

    # Добавляем ваш ввод в историю
    history.append(f"Пользователь: {user_input}")

    # Формируем контекст для модели
    context = '\n'.join(history) + "\nМодель:"

    inputs = tokenizer(context, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=1000,
        do_sample=True,
        temperature=0.7,
        top_p=0.95,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Извлекаем только ответ модели
    response_lines = response[len(context):].strip().split('\n')
    if response_lines:
        model_reply = response_lines[0]
    else:
        model_reply = "(Нет ответа)"
    
    print(f"Модель: {model_reply}")
    history.append(f"Модель: {model_reply}")

