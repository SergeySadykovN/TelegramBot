import telebot
from PIL import Image, ImageOps
import io
from telebot import types
from token_ import TOKEN_

bot = telebot.TeleBot(TOKEN_)

# тут будем хранить информацию о действиях пользователя
user_states = {}

# набор стандартных символов для эффекта ASCII по умолчанию
ascii_symbols_stock = '@$%#*+=-:. '


def resize_image(image: Image.Image, new_width: int = 100) -> Image.Image:
    """
    Изменение размера изображения
    :param image: (Image.Image) Исходное изображение
    :param new_width: (int) Новая ширина изображения
    :return: Image.Image Измененное изображение
    """
    width, height = image.size
    ratio = height / width
    new_height = int(new_width * ratio)
    return image.resize((new_width, new_height))


def grayify(image: Image.Image) -> Image.Image:
    """Преобразование в оттенки серого
    """
    return image.convert("L")


def image_to_ascii(image_stream: io.BytesIO, ascii_chars: str, new_width: int = 40) -> str:
    """Конвертация изображения в ASCII-арт.
    :param image_stream: (io.BytesIO) поток байтов изображения
    :param new_width: (int) Новая ширина изображения для ASCII
    :param ascii_chars: (str) Набор символов для ASCII-арта
    :return: (str) Строка символов  c артом ASCII
    """
    # Переводим в оттенки серого
    image = Image.open(image_stream).convert('L')

    # меняем размер сохраняя отношение сторон
    width, height = image.size
    aspect_ratio = height / float(width)
    new_height = int(aspect_ratio * new_width * 0.55)  # 0,55 так как буквы выше чем шире
    img_resized = image.resize((new_width, new_height))

    img_str = pixels_to_ascii(img_resized, ascii_chars)
    img_width = img_resized.width

    max_characters = 4000 - (new_width + 1)
    max_rows = max_characters // (new_width + 1)

    ascii_art = ""
    for i in range(0, min(max_rows * img_width, len(img_str)), img_width):
        ascii_art += img_str[i:i + img_width] + "\n"

    return ascii_art


def pixels_to_ascii(image: Image.Image, ascii_chars: str) -> str:
    """Преобразование пикселей в ASCII-symbols
    :param image: (Image.Image) Изображение в оттенках
    :param ascii_chars: (str) Набор символов для ASCII-арта
    :return (str) Строка символов ASCII
    """
    pixels = image.getdata()
    characters = ""
    for pixel in pixels:
        characters += ascii_chars[pixel * len(ascii_chars) // 256]
    return characters


def pixelate_image(image: Image.Image, pixel_size: int) -> Image.Image:
    """Пикселизация изображения
    :param image: (Image.Image) Исходное изображение
    :param pixel_size: (int) Размер пикселя для пикселизации
    :return: Image.Image Пикселизированное изображение
    """
    image = image.resize(
        (image.size[0] // pixel_size, image.size[1] // pixel_size),
        Image.NEAREST
    )
    image = image.resize(
        (image.size[0] * pixel_size, image.size[1] * pixel_size),
        Image.NEAREST
    )
    return image


def invert_colors(image: Image.Image) -> Image.Image:
    """
    Инверсия цветов изображения
    :param image: (Image.Image) Исходное изображение
    :return: (Image.Image)  Изображение с инверсией цветов
    """
    return ImageOps.invert(image)


def mirror_image(image: Image.Image, mode: str) -> Image.Image:
    """
    Отражение изображения
    :param image: (Image.Image) Исходное изображение
    :param mode: (str) Режим отражения ("horizontal" или "vertical")
    :return: (image.Image) Отраженнное изображения
    """
    if mode == "horizontal":
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    elif mode == "vertical":
        return image.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        raise ValueError("Invalid mode for mirroring image. Use 'vertical' or 'horizontal'")


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: telebot.types.Message):
    """Обработка команд /start и /help.
    :param message: (telebot.types.Message) Сообщение от пользоваиеля
    """
    bot.reply_to(message, "Пришлите мне изображение, и я предложу вам варианты!")


@bot.message_handler(content_types=['photo'])
def handle_photo(message: telebot.types.Message):
    """ Обработка фотографий
    :param message: (telebot.types.Message) Сообщение с фотографией от пользоваиеля
    """
    bot.reply_to(message,
                 "Я получил вашу фотографию! Пожалуйста, выберите, что бы вы хотите с ней сделать?",
                 reply_markup=get_options_keyboard())
    user_states[message.chat.id] = {'photo': message.photo[-1].file_id}


def get_options_keyboard():
    """Клавиатура с варинтами обработок
    :return (types.InlineKeyboardMarkup) клава с кнопками для выбора оброботки
    """
    keyboard = types.InlineKeyboardMarkup()
    pixelate_btn = types.InlineKeyboardButton("Pixelate", callback_data="pixelate")
    ascii_btn = types.InlineKeyboardButton("ASCII Art", callback_data="ascii")
    invert_btn = types.InlineKeyboardButton("Invert Colors", callback_data="invert")
    mirror_horizont_btn = types.InlineKeyboardButton("Mirror horizontal", callback_data="mirror_horizontal")
    mirror_vert_btn = types.InlineKeyboardButton("Mirror Vertical", callback_data="mirror_vertical")

    keyboard.add(pixelate_btn, ascii_btn, invert_btn, mirror_horizont_btn, mirror_vert_btn)
    return keyboard


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call: telebot.types.CallbackQuery):
    """Обработка выбора пользователя
    :return (telebot.types.CallbackQuery) Объект с инфо о нажатой кнопке
    """
    if call.data == "pixelate":
        bot.answer_callback_query(call.id, "Пикселизация изображения...")
        pixelate_and_send(call.message)
    elif call.data == "ascii":
        bot.answer_callback_query(call.id, "Converting your image to ASCII art...")
        bot.send_message(call.message.chat.id, "Введите набор символов для ASCII-арта, "
                                               "начиная с самых темных к самым светлым,"
                                               "например ЖХУИЪЬою:,"
                                               "\nИли напишите 'default' для использования стандартного набора символов")
        bot.register_next_step_handler(call.message, ask_for_ascii_chairs)

    elif call.data == "invert":
        bot.answer_callback_query(call.id, "Inverting colors of your image...")
        invert_and_send(call.message)
    elif call.data == "mirror_horizontal":
        bot.answer_callback_query(call.id, "Mirroring your image horizontally...")
        mirror_and_send(call.message, "horizontal")
    elif call.data == "mirror_vertical":
        bot.answer_callback_query(call.id, "Mirroring your image vertically...")
        mirror_and_send(call.message, "vertical")


def ask_for_ascii_chairs(message: telebot.types.Message):
    """Запрос набора символов для арта ASCII
    :param message: (telebot.types.Message) Сообщение от пользователя с набором символов
    """
    ascii_chars = message.text
    if ascii_chars.lower() == 'default':
        ascii_chars = ascii_symbols_stock
    user_states[message.chat.id]['ascii_chairs'] = ascii_chars
    ascii_and_send(message)


def pixelate_and_send(message: telebot.types.Message):
    """
    Пикслелизация и отправка изображения
    :param message: (telebot.types.Message) Сообщение от пользователя
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    pixelated = pixelate_image(image, 20)

    output_stream = io.BytesIO()
    pixelated.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def ascii_and_send(message: telebot.types.Message):
    """Конвертация изображения в ASCII-арт и отправка результата.
    :param message: (telebot.types.Message) Сообщение от пользователя
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    ascii_chars = user_states[message.chat.id].get('ascii_chairs', '@%#*+=-:. ')
    ascii_art = image_to_ascii(image_stream, ascii_chars)
    bot.send_message(message.chat.id, f"```\n{ascii_art}\n```", parse_mode="MarkdownV2")


def invert_and_send(message: telebot.types.Message):
    """
    Инверсия цветов  и отправка изображения
    :param message: (telebot.types.Message) Сообщение от пользователя
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    inverted = invert_colors(image)

    output_stream = io.BytesIO()
    inverted.save(output_stream, format='JPEG')
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


def mirror_and_send(message: telebot.types.Message, mode: str):
    """Отражение и отправка изображения
    :param message: (telebot.types.Message) Сообщение от пользователя
    :param mode: (str) Режим отражения ("horizontal", "vertical" )
    """
    photo_id = user_states[message.chat.id]['photo']
    file_info = bot.get_file(photo_id)
    downloaded_file = bot.download_file(file_info.file_path)

    image_stream = io.BytesIO(downloaded_file)
    image = Image.open(image_stream)
    mirrored = mirror_image(image, mode)

    output_stream = io.BytesIO()
    mirrored.save(output_stream, format="JPEG")
    output_stream.seek(0)
    bot.send_photo(message.chat.id, output_stream)


bot.polling(none_stop=True)
