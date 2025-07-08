import json
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject


class MediaGroupMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        if isinstance(event.callback_query, CallbackQuery):
            callback_data = event.callback_query.data
            if 'first' in callback_data:
                bot = data['bot']
                user = data["event_from_user"]

                json_data = json.loads(callback_data)
                first_message = int(json_data['first'])
                last_message = int(json_data['last'])
                message_ids = list(range(first_message, last_message))
                await bot.delete_messages(chat_id=user.id, message_ids=message_ids)

                data['callback_data'] = json_data['act']

        return await handler(event, data)
