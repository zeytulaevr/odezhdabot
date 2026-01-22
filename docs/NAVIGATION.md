# Система навигации с кнопкой "Назад"

## Обзор

Реализована полноценная система навигации со Stack истории экранов для корректной работы кнопки "Назад" во всех частях бота.

## Компоненты

### 1. NavigationStack (`src/utils/navigation.py`)

Основной класс для управления историей навигации в FSM state.

**Методы:**
- `push()` - добавить экран в историю
- `pop()` - извлечь предыдущий экран
- `clear()` - очистить историю
- `get_history_size()` - получить размер истории

**Лимиты:**
- Максимум 20 экранов в стеке (автоматическая очистка старых)

### 2. Хелперы

#### `edit_message_with_navigation()`
Редактирует сообщение и автоматически сохраняет его в историю.

```python
await edit_message_with_navigation(
    callback=callback,
    state=state,
    text="Текст сообщения",
    markup=keyboard,
    save_to_history=True,  # по умолчанию
)
```

#### `send_message_with_navigation()`
Отправляет новое сообщение с сохранением в историю.

```python
await send_message_with_navigation(
    message=message,
    state=state,
    text="Текст",
    markup=keyboard,
)
```

#### `send_photo_with_navigation()`
Отправляет фото с текстом и сохранением в историю.

```python
await send_photo_with_navigation(
    message=message,
    state=state,
    photo=photo_file_id,
    caption="Описание",
    markup=keyboard,
)
```

#### `go_back()`
Возвращает на предыдущий экран из истории.

```python
success = await go_back(
    callback=callback,
    state=state,
    default_text="🏠 Главное меню",  # если история пуста
)
```

### 3. Обработчик кнопки "Назад"

Централизованный обработчик в `src/bot/handlers/common/navigation.py`:

```python
@router.callback_query(F.data == CallbackPrefix.BACK)
async def handle_back_button(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Обработчик кнопки 'Назад'."""
    await go_back(callback, state)
```

## Использование

### Базовый пример

```python
from src.utils.navigation import edit_message_with_navigation

@router.callback_query(F.data == "my_menu")
async def show_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    text = "📋 Мое меню"
    keyboard = get_my_keyboard()

    # Автоматически сохранит экран в историю
    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )
```

### Работа с фото

```python
from src.utils.navigation import NavigationStack

# Вручную сохраняем экран с фото
await NavigationStack.push(
    state=state,
    text=caption,
    markup=keyboard,
    photo_file_id=product.photo_file_id,
    callback_data=callback.data,
)

# Отправляем фото
await callback.message.answer_photo(
    photo=product.photo_file_id,
    caption=caption,
    reply_markup=keyboard,
)
```

### Очистка истории

При входе в основные разделы рекомендуется очищать историю:

```python
@router.message(Command("superadmin"))
async def cmd_superadmin(
    message: Message,
    state: FSMContext,
) -> None:
    # Очищаем историю при входе в панель
    await NavigationStack.clear(state)

    await message.answer(
        text="Супер-админ панель",
        reply_markup=keyboard,
    )
```

### Отключение сохранения

Если не нужно сохранять экран в историю:

```python
await edit_message_with_navigation(
    callback=callback,
    state=state,
    text=text,
    markup=keyboard,
    save_to_history=False,  # не сохранять
)
```

## Особенности реализации

1. **Сериализация клавиатур**: InlineKeyboardMarkup автоматически сериализуется в JSON для хранения в FSM state.

2. **Поддержка фото**: Система хранит `photo_file_id` и корректно восстанавливает экраны с фото.

3. **Лимит стека**: Автоматически ограничивает размер до 20 элементов, удаляя самые старые.

4. **Graceful degradation**: Если история пуста, кнопка "Назад" показывает главное меню.

## Обновленные обработчики

### SuperAdmin
- ✅ `superadmin/menu.py` - главная панель и меню
- ✅ `superadmin/categories.py` - управление категориями
- ✅ `superadmin/products/manage.py` - управление товарами

### User
- Требуется обновление при появлении каталога

## Примеры использования в коде

### Список категорий
```python
# src/bot/handlers/superadmin/categories.py:28
@router.callback_query(F.data == "categories_manage", IsSuperAdmin())
async def categories_list(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Список категорий."""
    category_repo = CategoryRepository(session)
    categories = await category_repo.get_all()

    text = f"📁 <b>Управление категориями</b>..."
    keyboard = get_categories_manage_keyboard(categories)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )
```

### Просмотр товара с фото
```python
# src/bot/handlers/superadmin/products/manage.py:103
@router.callback_query(F.data.startswith("prod_view:"), IsSuperAdmin())
async def view_product(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    product = await product_service.get_product(product_id)

    if product.photo_file_id:
        # Вручную сохраняем с фото
        await NavigationStack.push(
            state=state,
            text=text,
            markup=keyboard,
            photo_file_id=product.photo_file_id,
            callback_data=callback.data,
        )

        await callback.message.delete()
        await callback.message.answer_photo(
            photo=product.photo_file_id,
            caption=text,
            reply_markup=keyboard,
        )
    else:
        # Используем хелпер для обычного текста
        await edit_message_with_navigation(
            callback=callback,
            state=state,
            text=text,
            markup=keyboard,
        )
```

## Тестирование

Для тестирования навигации:

1. Откройте супер-админ панель: `/superadmin`
2. Перейдите: Товары → Список товаров → Просмотр товара
3. Нажмите кнопку "◀️ Назад" - должен вернуться к списку
4. Еще раз "Назад" - вернется в меню товаров
5. Еще раз "Назад" - вернется в супер-админ панель

То же самое для категорий:
1. Категории → Просмотр категории → "Назад"

## Будущие улучшения

- [ ] Добавить навигацию в user обработчики (каталог, товары)
- [ ] Добавить breadcrumbs (хлебные крошки) для отображения пути
- [ ] Поддержка named screens для прямых переходов
- [ ] Аналитика использования навигации
