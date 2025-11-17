import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from jdatetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display
from matplotlib.ticker import FuncFormatter
import math
import os

# ===============================================================
# بخش تنظیمات و توابع مشترک
# ===============================================================

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

try:
    font_path = "Vazirmatn-FD-ExtraBold.ttf"
    if not os.path.exists(font_path):
        raise FileNotFoundError
    font_prop = fm.FontProperties(fname=font_path)
    print("فونت Vazirmatn با موفقیت بارگذاری شد.")
except FileNotFoundError:
    print("هشدار: فایل فونت 'Vazirmatn-FD-ExtraBold.ttf' یافت نشد. از فونت پیش‌فرض استفاده می‌شود.")
    font_prop = fm.FontProperties()

# --- توابع کمکی ---
def reshape_text(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def to_persian_digits(text):
    english_digits = "0123456789"
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    translation_table = str.maketrans(english_digits, persian_digits)
    return str(text).translate(translation_table)

def thousands_formatter(x, pos):
    formatted_number = f'{int(x):,}'
    return to_persian_digits(formatted_number)

# ===============================================================
# تابع ۱: تولید نمودارهای بازار آپشن
# ===============================================================
def generate_options_plots():
    print("\n--- شروع فرآیند تولید نمودارهای بازار آپشن (۲۵۰ روز) ---")
    URL = 'https://tradersarena.ir/options-arena/history'
    NOW = datetime.now()
    NOW_STR = NOW.strftime('%Y/%m/%d | %H:%M:%S')
    NOW_FILE_STR = NOW.strftime('%Y-%m-%d')
    channel_name = "کانال تلگرام : Data_Bors"
    generated_files = []

    try:
        print(f"در حال دریافت داده از: {URL}")
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        bs = BeautifulSoup(response.text, 'html.parser')
        table = bs.find('table', class_='sticky market')
        if not table:
            print("خطا: جدول داده‌های آپشن یافت نشد.")
            return []

        data = []
        rows = table.find_all('tr')[2:182] 
        print(f"تعداد {len(rows)} ردیف داده برای آپشن دریافت شد.")

        for tr in rows:
            cols = tr.find_all('td')
            if len(cols) > 14:
                tarikh = cols[1].text.strip()
                kol = float(cols[2].text.replace(' B', '').replace(',', '').strip())
                ekhtyar_kharyd = float(cols[8].text.replace(' B', '').replace(',', '').strip())
                ekhtyar_forosh = float(cols[14].text.replace(' B', '').replace(',', '').strip())
                if all(v is not None and v != 0 for v in [kol, ekhtyar_kharyd, ekhtyar_forosh]):
                    data.append({
                        "تاریخ": tarikh, 'ارزش معاملات کل': kol,
                        'ارزش معاملات اختیار خرید': ekhtyar_kharyd, 'ارزش معاملات اختیار فروش': ekhtyar_forosh
                    })

        if not data:
            print("داده‌ای برای پردازش در بازار آپشن وجود ندارد.")
            return []
        
        df = pd.DataFrame(data)
        df_reversed = df.iloc[::-1].reset_index(drop=True)
        df_reversed['MA_5_kol'] = df_reversed['ارزش معاملات کل'].rolling(window=5).mean()
        df_reversed['MA_10_kol'] = df_reversed['ارزش معاملات کل'].rolling(window=10).mean()
        df_reversed['MA_30_kol'] = df_reversed['ارزش معاملات کل'].rolling(window=30).mean()
        df = pd.merge(df, df_reversed.iloc[::-1], on='تاریخ', how='left', suffixes=('', '_y'))
        df = df.loc[:,~df.columns.str.endswith('_y')]

        # --- نمودار ۱: نمای کلی معاملات آپشن (سه‌قسمتی) ---
        # <<< تغییر اصلی اینجا اعمال شده است >>>
        fig1, (ax0, ax1, ax2) = plt.subplots(3, 1, figsize=(20, 11), sharex=True)
        
        fig1.suptitle(reshape_text(f"گزارش ارزش معاملات اختیار خرید و فروش | بروزرسانی: {to_persian_digits(NOW_STR)}"), fontsize=18, fontproperties=font_prop, y=0.98, color='#003366')
        
        last_date_option = to_persian_digits(df["تاریخ"].iloc[0])
        last_val_total = to_persian_digits(f'{df["ارزش معاملات کل"].iloc[0]:,.0f}')
        title0 = f'نمودار ارزش معاملات کل اختیارها | آخرین مقدار ({last_date_option}): {last_val_total} میلیارد تومان'
        ax0.plot(df['تاریخ'], df['ارزش معاملات کل'], label=reshape_text('ارزش معاملات کل'), color='#000000', marker='.', linewidth=1.5)
        ax0.set_title(reshape_text(title0), fontproperties=font_prop, fontsize=14)
        
        last_val_call = to_persian_digits(f'{df["ارزش معاملات اختیار خرید"].iloc[0]:,.0f}')
        title1 = f'نمودار ارزش معاملات اختیار خرید | آخرین مقدار ({last_date_option}): {last_val_call} میلیارد تومان'
        ax1.plot(df['تاریخ'], df['ارزش معاملات اختیار خرید'], label=reshape_text('ارزش معاملات اختیار خرید'), color='#158100', marker='.', linewidth=1.5)
        ax1.set_title(reshape_text(title1), fontproperties=font_prop, fontsize=14, color='#158100')
        
        last_val_put = to_persian_digits(f'{df["ارزش معاملات اختیار فروش"].iloc[0]:,.0f}')
        title2 = f'نمودار ارزش معاملات اختیار فروش | آخرین مقدار ({last_date_option}): {last_val_put} میلیارد تومان'
        ax2.plot(df['تاریخ'], df['ارزش معاملات اختیار فروش'], label=reshape_text('ارزش معاملات اختیار فروش'), marker='.', color='#990000', linewidth=1.5)
        ax2.set_title(reshape_text(title2), fontproperties=font_prop, fontsize=14, color='#990000')

        for ax in [ax0, ax1, ax2]:
            ax.set_ylabel(reshape_text('میلیارد تومان'), fontproperties=font_prop, fontsize=12)
            ax.legend(loc='upper left', prop=font_prop)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.yaxis.set_major_formatter(FuncFormatter(thousands_formatter))
            for label in ax.get_yticklabels(): label.set_fontproperties(font_prop)

        ax0.invert_xaxis()
        tick_spacing = math.ceil(len(df) / 20)
        plt.xticks(ticks=df['تاریخ'][::tick_spacing], rotation=60, ha='right', fontproperties=font_prop, fontsize=11)
        
        fig1.text(0.5, 0.02, reshape_text(channel_name), fontsize=14, va='bottom', ha='center', fontproperties=font_prop, color='#3399ff')
        plt.subplots_adjust(left=0.06, right=0.97, bottom=0.15, top=0.92, hspace=0.35)
        
        filename1 = f'OPTIONS_overview_{NOW_FILE_STR}.png'
        plt.savefig(filename1, dpi=300)
        generated_files.append(filename1)
        print(f"نمودار اول آپشن (نمای کلی) با نام '{filename1}' ذخیره شد.")
        plt.close(fig1)

        # --- نمودار ۲: ارزش معاملات کل آپشن با میانگین‌ها ---
        fig2, ax_ma_kol = plt.subplots(figsize=(14, 7.9))
        ax_ma_kol.plot(df['تاریخ'], df['ارزش معاملات کل'], label=reshape_text('ارزش معاملات کل'), color='grey', marker='.', linestyle='--', alpha=0.6)
        ax_ma_kol.plot(df['تاریخ'], df['MA_5_kol'], label=reshape_text('میانگین ۵ روز'), color='#ff7f0e', linewidth=2)
        ax_ma_kol.plot(df['تاریخ'], df['MA_10_kol'], label=reshape_text('میانگین ۱۰ روز'), color='#2ca02c', linewidth=2)
        ax_ma_kol.plot(df['تاریخ'], df['MA_30_kol'], label=reshape_text('میانگین ۳۰ روز'), color='#1f77b4', linewidth=2)
        
        last_total_value = to_persian_digits(f"{df['ارزش معاملات کل'].iloc[0]:,.0f}")
        last_date = to_persian_digits(df['تاریخ'].iloc[0])
        new_title = f'ارزش کل معاملات اختیار و میانگین‌ها | آخرین مقدار: {last_total_value} م.ت ({last_date})'
        ax_ma_kol.set_title(reshape_text(new_title), fontproperties=font_prop, fontsize=16, color='#003366')
        
        ax_ma_kol.set_ylabel(reshape_text('میلیارد تومان'), fontproperties=font_prop, fontsize=12)
        ax_ma_kol.legend(loc='upper left', prop=font_prop)
        ax_ma_kol.grid(True, linestyle='--', alpha=0.6)
        ax_ma_kol.yaxis.set_major_formatter(FuncFormatter(thousands_formatter))
        for label in ax_ma_kol.get_yticklabels(): label.set_fontproperties(font_prop)
        ax_ma_kol.invert_xaxis()
        plt.xticks(ticks=df['تاریخ'][::tick_spacing], rotation=60, ha='right', fontproperties=font_prop, fontsize=11)
        fig2.text(0.5, 0.01, reshape_text(channel_name), fontsize=14, va='bottom', ha='center', fontproperties=font_prop, color='#3399ff')
        plt.subplots_adjust(left=0.06, right=0.97, bottom=0.18, top=0.92)

        filename2 = f'OPTIONS_total_ma_{NOW_FILE_STR}.png'
        plt.savefig(filename2, dpi=300)
        generated_files.append(filename2)
        print(f"نمودار دوم آپشن (میانگین متحرک) با نام '{filename2}' ذخیره شد.")
        plt.close(fig2)

        print("--- فرآیند نمودارهای آپشن با موفقیت تمام شد ---")
        return generated_files

    except Exception as e:
        print(f"خطا در پردازش داده‌های آپشن: {e}")
        return []

# ===============================================================
# تابع ۲: تولید نمودار ارزش معاملات سهام خرد
# ===============================================================
def generate_stock_plot():
    print("\n--- شروع فرآیند تولید نمودار ارزش معاملات خرد ---")
    URL = 'https://tradersarena.ir/market/history?type=1'
    NOW = datetime.now()
    NOW_STR_TITLE = f'{NOW : %Y/%m/%d | %H:%M:%S }'
    NOW_STR_FILE = f'{NOW : %Y-%m-%d }'
    channel_name = "کانال تلگرام : Data_Bors"

    try:
        print(f"در حال دریافت داده از: {URL}")
        html = requests.get(URL, timeout=15)
        html.raise_for_status()
        bs = BeautifulSoup(html.text, 'html.parser')
        table = bs.find('table', attrs={'class': 'sticky market'})
        if not table:
            print("خطا: جدول داده‌های سهام خرد یافت نشد.")
            return None

        data = []
        trs = table.find_all('tr')[1:181]
        for tr in trs:
            tds = tr.find_all('td')
            if len(tds) > 3:
                data.append({"تاریخ": tds[1].text, 'ارزش معاملات': float(tds[2].text.replace(' B', ''))})

        if not data:
            print("داده‌ای برای پردازش در سهام خرد وجود ندارد.")
            return None

        df = pd.DataFrame(data).iloc[::-1].reset_index(drop=True)
        ma_periods = [30, 10, 5]
        for period in ma_periods:
            df[f'MA_{period}'] = df['ارزش معاملات'].rolling(window=period).mean()

        fig, ax = plt.subplots(figsize=(24, 10))
        colors = {30: 'crimson', 10: 'royalblue', 5: 'orange'}
        ax.bar(df['تاریخ'], df['ارزش معاملات'], label=reshape_text('ارزش معاملات روزانه'), color='lightgrey', alpha=0.7)
        for period in ma_periods:
            ax.plot(df['تاریخ'], df[f'MA_{period}'], label=reshape_text(f'میانگین {to_persian_digits(period)} روزه'), color=colors[period], linewidth=2.5)

        last_value_persian = to_persian_digits(f"{df['ارزش معاملات'].iloc[-1]:,.0f}")
        last_date_persian = to_persian_digits(df['تاریخ'].iloc[-1])
        now_str_persian = to_persian_digits(NOW_STR_TITLE)
        main_title = f'تحلیل ارزش معاملات خرد | آخرین مقدار: {last_value_persian} میلیارد تومان ({last_date_persian}) | بروزرسانی: {now_str_persian}'
        ax.set_title(reshape_text(main_title), fontproperties=font_prop, fontsize=18, color='#003366')

        ax.legend(loc='upper left', prop=font_prop, fontsize=12)
        ax.grid(True, linestyle='--', linewidth=0.5)
        ax.yaxis.set_major_formatter(FuncFormatter(thousands_formatter))
        for label in ax.get_yticklabels(): label.set_fontproperties(font_prop)
        ax.set_ylabel(reshape_text('میلیارد تومان'), fontproperties=font_prop, fontsize=16)
        tick_spacing = math.ceil(len(df) / 20)
        ax.set_xticks(df['تاریخ'][::tick_spacing])
        ax.tick_params(axis='x', rotation=60, labelsize=10)
        plt.setp(ax.get_xticklabels(), fontproperties=font_prop, ha='right')
        fig.text(0.5, -0.06, reshape_text(channel_name), fontsize=16, va='bottom', ha='center', fontproperties=font_prop, color='#3399ff', transform=fig.transFigure)

        filename = f'STOCK_value_analysis_{NOW_STR_FILE}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        print(f"نمودار سهام خرد با نام '{filename}' ذخیره شد.")
        return filename

    except Exception as e:
        print(f"خطا در پردازش داده‌های سهام خرد: {e}")
        return None

# ===============================================================
# تابع ۳: ارسال عکس به تلگرام
# ===============================================================
def send_photo_to_telegram(bot_token, chat_id, photo_path, caption=""):
    if not photo_path:
        print("خطا: مسیر عکسی برای ارسال وجود ندارد.")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    print(f"در حال ارسال {photo_path} به تلگرام...")
    try:
        with open(photo_path, 'rb') as photo_file:
            response = requests.post(url, files={'photo': photo_file}, data={'chat_id': chat_id, 'caption': caption})
            if response.status_code == 200:
                print("عکس با موفقیت به تلگرام ارسال شد.")
            else:
                print(f"خطا در ارسال به تلگرام: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"یک خطای ناشناخته در هنگام ارسال به تلگرام رخ داد: {e}")

# ===============================================================
# بخش اصلی اجرای برنامه (با هشتگ و حذف خودکار فایل‌ها)
# ===============================================================
if __name__ == "__main__":
    print("="*46)
    print("شروع اجرای اسکریپت ارسال گزارشات به تلگرام")
    print("="*46)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("خطای حیاتی: توکن ربات تلگرام یا شناسه چت تنظیم نشده است. برنامه متوقف می‌شود.")
    else:
        option_captions = [
            "📊 گزارش کلی ارزش معاملات بازار آپشن\n\n#ارزش_معاملات_اختیار #آپشن",
            "📈 تحلیل ارزش کل معاملات آپشن و میانگین‌های متحرک\n\n#میانگین_ارزش_معاملات_اختیار #آپشن"
        ]
        stock_caption = "📉 تحلیل ارزش معاملات سهام خرد\n\n#ارزش_معاملات_خرد #تحلیل_بازار #بورس"

        option_chart_files = generate_options_plots()
        if option_chart_files:
            for i, chart_file in enumerate(option_chart_files):
                send_photo_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, chart_file, option_captions[i])
                try:
                    os.remove(chart_file)
                    print(f"فایل موقت '{chart_file}' با موفقیت حذف شد.")
                except OSError as e:
                    print(f"خطا در حذف فایل '{chart_file}': {e}")
        else:
            print("هیچ نموداری برای بازار آپشن تولید نشد.")

        stock_chart_file = generate_stock_plot()
        if stock_chart_file:
            send_photo_to_telegram(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, stock_chart_file, stock_caption)
            try:
                os.remove(stock_chart_file)
                print(f"فایل موقت '{stock_chart_file}' با موفقیت حذف شد.")
            except OSError as e:
                print(f"خطا در حذف فایل '{stock_chart_file}': {e}")
        else:
            print("نموداری برای ارزش معاملات خرد تولید نشد.")

    print("\n" + "="*46)
    print("اجرای اسکریپت به پایان رسید.")
    print("="*46)
