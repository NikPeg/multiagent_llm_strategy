import logging
import torch
from typing import List
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

def format_conversation_history(history: List[str]) -> str:
    return '\n'.join(history)

def sync_generate_response(user_id, message_text, system_prompt, model, tokenizer, history_limit):
    """Генерирует ответ модели на сообщение пользователя с учетом истории диалога"""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Получаем историю диалога
        history = loop.run_until_complete(get_history(user_id))

        logger.info(f"Получена история диалога для пользователя {user_id}, {len(history)} сообщений")

        # Форматируем историю для использования в промпте
        formatted_history = ""
        if history:
            formatted_history = format_conversation_history(history)
            logger.debug(f"Форматированная история: {formatted_history[:200]}...")

        # Формируем промпт с историей и системным промптом
        if formatted_history:
            context = f"{system_prompt}\n\n{formatted_history}\nPlayer: {message_text}\nGame referee:"
        else:
            # Если истории нет, используем только текущее сообщение
            context = f"{system_prompt}\n\nPlayer: {message_text}\nGame referee:"

        logger.debug(f"Контекст для модели: {context[:200]}...")

        # Токенизируем контекст
        inputs = tokenizer(context, return_tensors="pt").to(model.device)

        try:
            # Генерируем ответ
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id
            )

            # Декодируем ответ
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Извлекаем только часть ответа, которая следует за промптом
            assistant_reply = response[len(context):].strip()

            # Проверяем, что ответ не пустой
            if not assistant_reply or assistant_reply.strip() == "":
                assistant_reply = "Как судья игры, я должен ответить на ваш запрос. Пожалуйста, опишите ваши следующие действия или задайте более конкретный вопрос о текущей ситуации в мире."

            # Обрабатываем многострочный ответ
            if '\n' in assistant_reply:
                clean_lines = []
                for line in assistant_reply.split('\n'):
                    # Удаляем строки, которые могут быть началом нового сообщения пользователя
                    if not line.strip().startswith('Player:') and not line.strip().startswith('User:'):
                        clean_lines.append(line)
                assistant_reply = '\n'.join(clean_lines)

            # Последняя проверка на пустой ответ
            if not assistant_reply or assistant_reply.strip() == "":
                assistant_reply = "Извините, произошла техническая ошибка. Продолжайте вашу игру, опишите следующие действия вашей страны."

            logger.info(f"Сгенерирован ответ длиной {len(assistant_reply)} символов")

        except Exception as gen_error:
            logger.error(f"Ошибка при генерации ответа: {str(gen_error)}", exc_info=True)
            assistant_reply = "Произошла техническая ошибка в работе модели. Пожалуйста, попробуйте еще раз."

        # Обновляем историю диалога
        loop.run_until_complete(update_history(user_id, message_text, assistant_reply, history_limit))
        loop.close()
        return assistant_reply
    except Exception as e:
        logger.error(f"Ошибка в generate_response: {str(e)}", exc_info=True)
        return "Извините, произошла внутренняя ошибка. Пожалуйста, попробуйте позже."
