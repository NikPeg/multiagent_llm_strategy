from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_name = "tiiuae/falcon-40b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

input_text = "Привет, Falcon! Расскажи что-нибудь интересное."
inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

with torch.no_grad():
    output = model.generate(**inputs, max_new_tokens=100)
    print(tokenizer.decode(output[0], skip_special_tokens=True))

