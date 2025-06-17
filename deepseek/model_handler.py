import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from database import get_history, update_history
from utils import *
from config import MAX_NEW_TOKENS, SHORT_NEW_TOKENS
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ModelHandler:
    def __init__(self, max_new_tokens, short_new_tokens):
        self.max_new_tokens = max_new_tokens
        self.short_new_tokens = short_new_tokens
        self._initialize_model()

    def _initialize_model(self):
        model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            use_flash_attention_2=False
        )

        # Log device information
        device_info = f"Модель использует устройство: {self.model.device}"
        logger.info(device_info)
        cuda_available = torch.cuda.is_available()
        logger.info(f"CUDA доступен: {cuda_available}")

        if cuda_available:
            cuda_device_count = torch.cuda.device_count()
            cuda_device_name = torch.cuda.get_device_name(0) if cuda_device_count > 0 else "Нет"
            logger.info(f"Количество GPU: {cuda_device_count}")
            logger.info(f"Название GPU: {cuda_device_name}")
            logger.info(f"Текущее использование GPU памяти: {torch.cuda.memory_allocated() / 1024**2:.2f} МБ")
            logger.info(f"Максимальная доступная GPU память: {torch.cuda.get_device_properties(0).total_memory / 1024**2:.2f} МБ")

    def sync_generate_response(self, user_id, message_text, rpg_prompt, country_name=None, country_desc=None, history_limit=4):
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            history = loop.run_until_complete(get_history(user_id))

            context_prompts = [rpg_prompt]
            if country_name and country_desc:
                context_prompts.append(
                    f'Игрок управляет страной {country_name}.\nОписание страны: {country_desc}\n'
                )
            context = '\n'.join(context_prompts + history + [f"Игрок: {message_text}"]) + "\nАссистент:"

            inputs = self.tokenizer(context, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Чистим ответ ассистента
            ai_response = clean_ai_response(response[len(context):].strip())

            loop.run_until_complete(update_history(user_id, message_text, ai_response, history_limit))
            loop.close()
            return ai_response, response
        except Exception as e:
            logger.error(f"Ошибка в generate_response: {str(e)}", exc_info=True)
            raise

    def generate_short_responce(self, prompt: str) -> str:
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.short_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Чистим ответ ассистента
            ai_response = clean_ai_response(response[len(prompt):].strip())

            loop.close()
            return ai_response
        except Exception as e:
            logger.error(f"Ошибка в generate_short_response: {str(e)}", exc_info=True)
            raise

model_handler = ModelHandler(MAX_NEW_TOKENS, SHORT_NEW_TOKENS)
executor = ThreadPoolExecutor(max_workers=1)
