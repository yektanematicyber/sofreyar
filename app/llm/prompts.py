from datetime import date
from app.llm.interface import MealType, PantryItemInput

SYSTEM_PROMPT = """شما «سفره‌یار» هستید؛ سرآشپز هوشمند و مشاور مهربان آشپزی ایرانی.
وظیفه شما این است که با توجه به موجودی مواد غذایی در انبار/یخچال کاربر، دقیقاً ۳ دستور پخت کاربردی، خوشمزه و واقع‌گرایانه پیشنهاد دهید.

قوانین اساسی:
۱. زبان خروجی: کاملاً به زبان فارسی، با لحنی ساده، صمیمی، دلگرم‌کننده و روان.
۲. اولویت با مواد رو به انقضا: موادی که تاریخ انقضای آن‌ها نزدیک‌تر است در اولویت اول مصرف قرار دارند تا از هدررفت غذا جلوگیری شود.
۳. تفکیک دقیق موجودی:
   - تنها موادی که در لیست ارسالی کاربر وجود دارند می‌توانند وضعیت in_pantry: true داشته باشند و باید در فیلد uses ثبت شوند.
   - هر ماده غذایی ضروری دیگر برای دستور پخت که در لیست کاربر نیست (حتی نمک، فلفل، روغن یا آب) باید in_pantry: false بوده و نام آن در فیلد missing آورده شود.
۴. ارزش غذایی:
   - مقادیر تغذیه‌ای (nutrition) به ازای «یک وعده» (per serving) و کاملاً تقریبی است.
   - از آوردن اعداد غیرواقعی و بیش از حد دقیق با اعشار مصنوعی خودداری کنید (مثلاً ۲۵۰ کالری، ۲۰ گرم پروتئین).
۵. ساختار خروجی:
   - خروجی باید تنها و تنها یک JSON Array معتبر شامل دقیقاً ۳ شیء دستور پخت (Recipe) باشد.
   - هیچ متن اضافی، توضیح سلام و احوال‌پرسی یا تگ مارک‌داون (مانند ```json یا ```) در ابتدا یا انتهای خروجی نباید وجود داشته باشد.
۶. موارد خاص و اقلام اندک:
   - حتی اگر اقلام موجود در انبار بسیار کم، ناکافی یا نامتعارف باشند، همچنان باید دقیقاً ۳ دستور غذا پیشنهاد دهید و اقلام کمبود را در فیلد missing ذکر کنید.

فرمت دقیق JSON برای هر دستور:
[
  {
    "title": "عنوان جذاب غذا",
    "summary": "توضیح کوتاه و صمیمی درباره غذا در ۱ الی ۲ جمله",
    "emoji": "یک اموجی مرتبط",
    "time_minutes": 25,
    "difficulty": "easy",
    "servings": 2,
    "ingredients": [
      {
        "name": "نام دقیق ماده",
        "amount": 2.0,
        "unit": "piece",
        "in_pantry": true
      }
    ],
    "uses": ["نام موادی که از انبار کاربر برداشته شده"],
    "missing": ["نام موادی که کاربر باید تهیه کند"],
    "steps": [
      "مرحله اول...",
      "مرحله دوم..."
    ],
    "nutrition": {
      "calories": 300,
      "protein_g": 15.0,
      "fiber_g": 3.0,
      "carbs_g": 30.0,
      "fat_g": 10.0
    }
  }
]"""

MEAL_TYPE_PERSIAN = {
    "breakfast": "صبحانه",
    "lunch": "ناهار",
    "dinner": "شام",
    "snack": "میان‌وعده",
}


def build_user_prompt(
    pantry_items: list[PantryItemInput],
    meal_type: MealType,
    servings: int,
) -> str:
    """Builds the user prompt, prioritizing items expiring soonest."""
    # Partition and sort: items with expiry_date ascending first, then items without expiry
    items_with_expiry = [item for item in pantry_items if item.expiry_date is not None]
    items_without_expiry = [item for item in pantry_items if item.expiry_date is None]

    items_with_expiry.sort(key=lambda x: x.expiry_date)  # type: ignore[arg-type]
    sorted_items = items_with_expiry + items_without_expiry

    today = date.today()

    inventory_lines = []
    for item in sorted_items:
        if item.expiry_date:
            days_left = (item.expiry_date - today).days
            if days_left < 0:
                expiry_info = f"منقضی شده ({abs(days_left)} روز پیش)"
            elif days_left == 0:
                expiry_info = "انقضا: امروز! (اولویت فوری مصرف)"
            elif days_left <= 3:
                expiry_info = f"انقضا: {item.expiry_date} ({days_left} روز مانده - اولویت بالا)"
            else:
                expiry_info = f"انقضا: {item.expiry_date} ({days_left} روز مانده)"
        else:
            expiry_info = "بدون تاریخ انقضا"

        inventory_lines.append(
            f"- {item.name}: {item.quantity} {item.unit} ({expiry_info})"
        )

    inventory_text = (
        "\n".join(inventory_lines)
        if inventory_lines
        else "هیچ ماده‌ای در انبار ثبت نشده است."
    )

    meal_type_fa = MEAL_TYPE_PERSIAN.get(meal_type, meal_type)

    prompt = f"""اطلاعات درخواست کاربر:
- وعده غذایی مورد نظر: {meal_type_fa} ({meal_type})
- تعداد نفرات (servings): {servings} نفر

موجودی انبار و یخچال کاربر (مرتب‌شده بر اساس نزدیک‌ترین تاریخ انقضا در ابتدا):
{inventory_text}

یادآوری الزامات حیاتی:
۱. اقلام دارای انقضای نزدیک‌تر را در اولویت مصرف قرار دهید.
۲. تنها موادی که در لیست بالا هستند in_pantry: true می‌گیرند و در فیلد uses قرار دارند. هر چیز دیگری در missing و in_pantry: false قرار گیرد.
۳. خروجی باید فقط و فقط یک JSON Array معتبر شامل دقیقاً ۳ دستور غذا باشد، بدون هیچ توضیح اضافی یا کد مارک‌داون.
"""
    return prompt


def build_retry_prompt(
    original_prompt: str,
    raw_response: str,
    error_message: str,
) -> str:
    """Builds a correction prompt for one-shot retry when validation fails."""
    # Truncate raw response if excessively long to avoid token explosion
    truncated_response = raw_response[:1000] if len(raw_response) > 1000 else raw_response
    return f"""پاسخ قبلی شما در اعتبارسنجی با خطای زیر مواجه شد:
خطا: {error_message}

بخشی از پاسخ نامعتبر قبلی شما:
{truncated_response}

لطفاً خطا را برطرف کرده و مجدداً یک JSON Array معتبر شامل «دقیقاً ۳ دستور پخت» مطابق با قالب درخواستی ارسال کنید.
مهم: هیچ علامت مارک‌داون (```)، هیچ متن مقدمه یا موخره ارسال نکنید؛ فقط آرایه خام JSON.

درخواست اصلی:
{original_prompt}
"""
