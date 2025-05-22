from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype="auto"  # Автоматически подберёт (обычно fp16 на современных GPU)
    # Можно явно указать torch.float16, если хотите: torch_dtype=torch.float16
)

history = []

print("=== DeepSeek-R1-Distill-Qwen-32B Chat (FP16)===")
print("Для выхода напишите 'выход' или 'exit'.\n")

while True:
    user_input = input("User: ")
    if user_input.lower() in ['выход', 'exit']:
        print("Диалог завершён.")
        break

    history.append(f"User: {user_input}")
    context = '\n'.join(history) + "\nAssistant:"

    inputs = tokenizer(context, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.95,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    response_lines = response[len(context):].strip().split('\n')
    if response_lines:
        model_reply = response_lines[0]
    else:
        model_reply = "(Нет ответа)"

    print(f"Assistant: {model_reply}")
    history.append(f"Assistant: {model_reply}")

