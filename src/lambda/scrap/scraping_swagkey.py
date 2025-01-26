from playwright.sync_api import sync_playwright, expect
from threading import Thread
import boto3
import re
from datetime import datetime, timezone, timedelta

ssm_client = boto3.client('ssm')
scrap_results = []

utc_now = datetime.now(timezone.utc)
seoul_timezone = timezone(timedelta(hours=9))
seoul_now = utc_now.astimezone(seoul_timezone)


def save_new_container_count(name, value):
    response = ssm_client.put_parameter(
        Name=name,
        Value=value,
        Type='String',
        Overwrite=True
    )
    return response


def get_prev_container_count(name):
    response = ssm_client.get_parameter(
        Name=name,
        WithDecryption=False
    )
    return int(response['Parameter']['Value'])


def exclude_special_string(origin, target):
    return origin.replace(target, '').strip()


def get_image_list(image_container):
    image_count = image_container.locator('img').count()
    image_list = []

    for j in range(image_count):
        image_locator = image_container.locator('img').nth(j)
        image_locator.wait_for(state='visible')
        image_src = image_locator.get_attribute('src')
        image_list.append(image_src)

    return image_list


def get_price(price_text):
    return re.sub(r'\D', '', price_text)


def get_price_unit(price_text):
    price_text = price_text.lower()

    if "달러" in price_text or "usd" in price_text or "$" in price_text:
        return "USD"

    if "원" in price_text or "krw" in price_text or "₩" in price_text:
        return "KRW"

    return "UNKNOWN"


def get_product_details(contents):
    # 상품 이름
    summary = contents.locator('#prod_goods_form')
    product_name = summary.locator('div.view_tit:not(.ns-icon.prod_icon)').text_content()
    product_name = exclude_special_string(product_name, '판매대기')
    product_name = exclude_special_string(product_name, '[예약판매]')
    product_name = exclude_special_string(product_name, '[GB]')
    product_name = exclude_special_string(product_name, '[Pre-order]')

    # 판매 기간
    period = contents.locator(
        'div.goods_summary p:has(span:has-text("판매기간")), '
        'div.goods_summary p:has(span:has-text("판매일정")), '
        'div.goods_summary p:has(span:has-text("판매 기간")), '
        'div.goods_summary p:has(span:has-text("판매 일정"))'
    ).text_content()

    # 상품 가격
    price_text = summary.locator('div.pay_detail .real_price').text_content()
    price = get_price(price_text)
    price_unit = get_price_unit(price_text)

    return [product_name, price, price_unit, period]


def get_category(product_name):
    product_name = product_name.lower()

    if "part" in product_name or "보강판" in product_name:
        return "PARTS"
    if "switch" in product_name or "스위치" in product_name:
        return "SWITCH"
    if "keycap" in product_name or "키캡" in product_name:
        return "KEYCAP"
    if "stabilizer" in product_name or "스타빌라이저" in product_name:
        return "STABILIZER"
    if "kit" in product_name or "키트" in product_name:
        return "KIT"

    return "KEYBOARD"


def get_iso_date(date):
    numbers = re.findall(r'\d+', date)

    if len(numbers) == 0 or len(numbers) > 6:
        raise ValueError("Invalid date format")

    current_year = datetime.now().year
    double_digit_year = current_year % 100

    if int(numbers[0]) >= double_digit_year:
        # date: 년, 월, 일, 시간, 분, 초 리스트
        date = [0] * 6
        if (len(numbers[0])) == 2:
            date[0] = 2000 + int(numbers[0])
        else:
            date[0] = int(numbers[0])

        # 그 다음 숫자부터 월, 일, 시간, 분, 초 추출
        idx = 1
        while idx < len(numbers):
            date[idx] = int(numbers[idx])
            idx += 1

    else:  # 년도 명시 안된 경우
        date = [0] * 6
        date[0] = current_year
        idx = 0

        # 첫 숫자부터 월, 일, 시간, 분, 초 추출
        while idx < len(numbers):
            date[idx + 1] = int(numbers[idx])
            idx += 1

    iso_date = f"{date[0]:04d}-{date[1]:02d}-{date[2]:02d}T{date[3]:02d}:{date[4]:02d}:{date[5]:02d}+09:00"

    return iso_date


def get_start_date(period):
    period = period.lower()
    period = exclude_special_string(period, "판매기간")
    period = exclude_special_string(period, "판매일정")
    period = period.split("~")

    if len(period) == 1 and "부터" not in period[0]:
        return None

    if len(period) == 1:
        start_date = period[0].strip()
    elif len(period) == 2:
        start_date = period[0].strip()
    else:
        raise ValueError("Invalid period format")

    if "부터" in start_date:
        start_date = exclude_special_string(start_date, "부터")
    elif "from" in start_date:
        start_date = exclude_special_string(start_date, "from")
    elif "start" in start_date:
        start_date = exclude_special_string(start_date, "start")

    while start_date[0] == " " or start_date[0] == ":":
        start_date = start_date[1:]

    return get_iso_date(start_date)


def get_end_date(period):
    period = period.lower()
    period = exclude_special_string(period, "판매기간")
    period = exclude_special_string(period, "판매일정")
    period = period.split("~")

    if len(period) == 1 and "까지" not in period[0] and "to" not in period[0]:
        return None

    if len(period) == 1:
        end_date = period[0].strip()
    elif len(period) == 2:
        end_date = period[1].strip()
    else:
        raise ValueError("Invalid period format")

    if "까지" in end_date:
        end_date = exclude_special_string(end_date, "까지")

    while end_date[0] == " " or end_date[0] == ":":
        end_date = end_date[1:]

    return get_iso_date(end_date)


def get_period_status(start_date, end_date):
    now = seoul_now.strftime("%Y-%m-%dT%H:%M:%S+09:00")
    if not start_date and not end_date:
        return "UNKNOWN"

    if not start_date:
        start_date = now

    if not end_date:
        end_date = now

    if start_date <= now <= end_date:
        return "IN_PROGRESS"

    if now < start_date:
        return "NOT_YET"

    if now > end_date:
        return "DONE"

    return "UNKNOWN"


def scrap(container, page):
    container.click()
    page.wait_for_selector('div.inside[doz_type="inside"]', state='visible')
    contents = page.locator('div.inside[doz_type="inside"]')

    page.wait_for_selector('div.owl-stage', state='visible')
    image_container = contents.locator('div.owl-stage')

    image_list = get_image_list(image_container)
    product_name, price, price_unit, period = get_product_details(contents)

    category = get_category(product_name)
    start_date = get_start_date(period)
    end_date = get_end_date(period)
    period_status = get_period_status(start_date, end_date)

    scrap_results.append({
        "product_name": product_name,
        "price": price,
        "unit": price_unit,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "period_status": period_status,
        "product_url": page.url,
        "image_url": image_list,
    })

    page.go_back(wait_until='domcontentloaded', timeout=0)


def count_is_changed(new_count, prev_count):
    if new_count == prev_count:
        return False
    return True


def run():
    playwright = sync_playwright().start()
    chromium = playwright.chromium
    browser = chromium.launch(headless=True,
                              args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--single-process'])

    page = browser.new_page()
    page.goto("https://www.swagkey.kr/47")

    # 페이지 로드 대기
    page.wait_for_load_state('domcontentloaded')

    main_container = page.locator('div.inside')

    new_container_count = int(main_container.locator('.text-brand._unit').text_content())
    prev_container_count = get_prev_container_count('swagkey-container-count')
    if not count_is_changed(new_container_count, prev_container_count):
        return scrap_results

    content_containers = main_container.locator('.item-overlay')
    container_count = new_container_count - prev_container_count

    for i in range(container_count):
        container = content_containers.nth(i)
        expect(container).to_be_visible()

        if not container.is_visible():
            continue

        try:
            scrap(container, page)
        except Exception as e:
            print("Exception: ", e)
            return {
                'status_code': 500,
                'from': 'swagkey',
                'body': {
                    'error': str(e)
                }
            }

    save_new_container_count('swagkey-container-count', str(new_container_count))
    page.close()
    browser.close()
    playwright.stop()


def handler(event, context):
    thread = Thread(target=run)
    thread.start()
    thread.join()

    if not scrap_results:
        return {
            'status_code': 204,
            'from': 'swagkey',
            'body': 'No content to scrap'
        }

    return {
        'status_code': 200,
        'from': 'swagkey',
        'bucket_name': 'bucket-for-scraping-lambda',
        'body': scrap_results
    }
