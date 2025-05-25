import logging
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from database import get_history, update_history

logger = logging.getLogger(__name__)

def init_model():
    """Инициализирует и возвращает модель и токенизатор"""
    logger.info("Инициализация модели...")

    model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.float16,
        use_flash_attention_2=False
    )

    # Логирование информации об устройстве
    device_info = f"Модель использует устройство: {model.device}"
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

    return model, tokenizer

def sync_generate_response(user_id, message_text, system_prompt, model, tokenizer, history_limit):
    """Генерирует ответ модели на сообщение пользователя"""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        history = loop.run_until_complete(get_history(user_id))

        # Добавляем системный промпт к контексту
        context = system_prompt + "\n\n" + '\n'.join(history + [f"Игрок: {message_text}"]) + "\nСудья игры:"

        inputs = tokenizer(context, return_tensors="pt").to(model.device)

        try:
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
            assistant_reply = response[len(context):].strip()

            # Проверяем, что ответ не пустой
            if not assistant_reply or assistant_reply.strip() == "":
                assistant_reply = "Как судья игры, я должен ответить на ваш запрос. Пожалуйста, опишите ваши следующие действия или задайте более конкретный вопрос о текущей ситуации в мире."

            # Обрабатываем многострочный ответ
            if '\n' in assistant_reply:
                clean_lines = []
                for line in assistant_reply.split('\n'):
                    if not line.strip().startswith('Игрок:') and not line.strip().startswith('User:'):
                        clean_lines.append(line)
                assistant_reply = '\n'.join(clean_lines)

            # Последняя проверка на пустой ответ
            if not assistant_reply or assistant_reply.strip() == "":
                assistant_reply = "Извините, произошла техническая ошибка. Продолжайте вашу игру, опишите следующие действия вашей страны."

        except Exception as gen_error:
            logger.error(f"Ошибка при генерации ответа: {str(gen_error)}", exc_info=True)
            assistant_reply = "Произошла техническая ошибка в работе модели. Пожалуйста, попробуйте еще раз."

        loop.run_until_complete(update_history(user_id, message_text, assistant_reply, history_limit))
        loop.close()
        return assistant_reply
    except Exception as e:
        logger.error(f"Ошибка в generate_response: {str(e)}", exc_info=True)
        return "Извините, произошла внутренняя ошибка. Пожалуйста, попробуйте позже."
