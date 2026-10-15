import streamlit as st
import sqlite3
import pandas as pd
import zipfile
import os

st.set_page_config(page_title="Gold Data Pipeline", page_icon="🪙", layout="wide")

st.title("🪙 سامانه خودکار جمع‌آوری و مدیریت داده‌های طلا")
st.markdown("سامانه جامع مدیریت، استانداردسازی و پایش متغیرهای کلان اقتصادی و بازارهای مالی")

ZIP_PATH = "economic_data.zip"
DB_PATH = "economic_data.db"

# استخراج فایل زیپ دیتابیس در صورت نیاز
if os.path.exists(ZIP_PATH) and not os.path.exists(DB_PATH):
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(".")

# ایجاد ۳ تب برای داشبورد، افزودن هوشمند متغیر و مدیریت/حذف
tab1, tab2, tab3 = st.tabs([
    "📊 داشبورد و نمودارها", 
    "➕ افزودن هوشمند متغیر (عامل)", 
    "⚙️ مدیریت و حذف متغیرها"
])

# ==========================================
# تب اول: داشبورد نمایشی، جداول و دانلود اکسل
# ==========================================
with tab1:
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            query = """
                SELECT s.series_code, s.title, s.frequency, o.observation_date, o.value
                FROM series_registry s
                JOIN standardized_observations o ON s.id = o.series_id
                WHERE UPPER(TRIM(s.status)) = 'ACTIVE'
                ORDER BY s.series_code, o.observation_date
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df.empty:
                df['observation_date'] = pd.to_datetime(df['observation_date'])
                
                st.subheader("📊 آخرین مقادیر فاندامنتال (Latest Summary)")
                latest_data = df.sort_values('observation_date').groupby('series_code').tail(1)
                latest_data = latest_data[['series_code', 'title', 'observation_date', 'value']].reset_index(drop=True)
                latest_data['observation_date'] = latest_data['observation_date'].dt.date
                st.dataframe(latest_data, use_container_width=True)

                @st.cache_data
                def convert_df_to_excel(df_to_convert):
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_to_convert.to_excel(writer, index=False, sheet_name='Data')
                    return output.getvalue()

                st.download_button(
                    label="📥 دانلود کل تاریخچه داده‌ها به صورت اکسل",
                    data=convert_df_to_excel(df),
                    file_name="economic_data_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                st.subheader("📈 نمودارهای روند تاریخی")
                series_codes = df['series_code'].unique()
                selected_series = st.selectbox("انتخاب متغیر برای مشاهده نمودار:", series_codes)
                if selected_series:
                    series_df = df[df['series_code'] == selected_series]
                    st.line_chart(series_df.set_index('observation_date')['value'])
            else:
                st.warning("⚠️ جدول‌ها در دیتابیس خالی هستند.")
                
        except Exception as e:
            st.error(f"❌ خطا در خواندن دیتابیس: {e}")
    else:
        st.warning("⚠️ فایل دیتابیس یافت نشد.")

# ==========================================
# تب دوم: افزودن هوشمند متغیر (مشابه سبک جستجو و پیشنهاد)
# ==========================================
with tab2:
    st.subheader("🔎 جستجو و افزودن هوشمند عامل (Series)")
    st.markdown("نام یا کلیدواژه انگلیسی عامل مورد نظر را وارد کنید تا پیشنهادات استاندارد یا ثبت مستقیم نمایش داده شود.")
    
    # بانک پیشنهادات پیش‌فرض رایج (مانند الگوهای یاهو و فرید)
    suggested_database = [
        {"code": "GOLDPRICE:GOLD", "title": "Gold Historical Daily Price", "frequency": "Daily"},
        {"code": "GOLDPRICE:SILVER", "title": "Silver Historical Daily Price", "frequency": "Daily"},
        {"code": "YAHOO:GC=F", "title": "Gold Futures", "frequency": "Daily"},
        {"code": "YAHOO:SI=F", "title": "Silver Futures", "frequency": "Daily"},
        {"code": "YAHOO:NQ=F", "title": "Nasdaq 100 Futures", "frequency": "Daily"},
        {"code": "YAHOO:^GSPC", "title": "S&P 500 Index", "frequency": "Daily"},
        {"code": "YAHOO:BNO", "title": "United States Brent Oil Fund", "frequency": "Daily"},
        {"code": "FRED:UNRATE", "title": "Unemployment Rate", "frequency": "Monthly"},
        {"code": "FRED:CPIAUCSL", "title": "Consumer Price Index (CPI)", "frequency": "Monthly"},
        {"code": "FRED:T10YIE", "title": "10-Year Breakeven Inflation Rate", "frequency": "Daily"}
    ]

    search_query = st.text_input("جستجوی عامل (به انگلیسی):", placeholder="مثلا Gold, Oil, CPI, S&P ...").strip().lower()

    if search_query:
        # فیلتر کردن پیشنهادات بر اساس جستجوی کاربر
        matches = [s for s in suggested_database if search_query in s['code'].lower() or search_query in s['title'].lower()]
        
        if matches:
            st.write(f"📌 **{len(matches)} پیشنهاد یافت شد:**")
            for idx, match in enumerate(matches):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.info(f"**{match['code']}** — {match['title']} ({match['frequency']})")
                with col_b:
                    if st.button("افزودن", key=f"add_match_{idx}"):
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM series_registry WHERE series_code = ?", (match['code'],))
                            if cursor.fetchone():
                                st.warning("⚠️ این متغیر از پیش در دیتابیس وجود دارد.")
                            else:
                                cursor.execute("""
                                    INSERT INTO series_registry (series_code, title, frequency, status)
                                    VALUES (?, ?, ?, 'ACTIVE')
                                """, (match['code'], match['title'], match['frequency']))
                                conn.commit()
                                st.success(f"✅ عامل {match['code']} با موفقیت اضافه شد!")
                            conn.close()
                        except Exception as e:
                            st.error(f"خطا: {e}")
        else:
            st.warning("موردی در پیشنهادات پیش‌فرض پیدا نشد. می‌توانید از طریق فرم سفارشی زیر عامل دلخواه خود را ثبت کنید.")

    st.markdown("---")
    st.write("### ✍️ ثبت سفارشی و دستی عامل جدید")
    with st.form("custom_add_form"):
        c1, c2 = st.columns(2)
        with c1:
            custom_code = st.text_input("کد دقیق (Series Code)", placeholder="مثلا YAHOO:CL=F")
            custom_freq = st.selectbox("فرکانس", ["Daily", "Weekly", "Monthly", "Quarterly", "Annual"])
        with c2:
            custom_title = st.text_input("عنوان توضیحی (Title)", placeholder="مثلا Crude Oil Futures")
            custom_status = st.selectbox("وضعیت اولیه", ["ACTIVE", "INACTIVE"])
            
        custom_submitted = st.form_submit_button("💾 ثبت عامل سفارشی")
        if custom_submitted:
            if not custom_code or not custom_title:
                st.error("لطفاً کد و عنوان را کامل وارد کنید.")
            else:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM series_registry WHERE series_code = ?", (custom_code,))
                    if cursor.fetchone():
                        st.warning("⚠️ این کد پیش‌تر ثبت شده است.")
                    else:
                        cursor.execute("""
                            INSERT INTO series_registry (series_code, title, frequency, status)
                            VALUES (?, ?, ?, ?)
                        """, (custom_code, custom_title, custom_freq, custom_status))
                        conn.commit()
                        st.success(f"✅ عامل سفارشی {custom_code} با موفقیت ثبت شد!")
                    conn.close()
                except Exception as e:
                    st.error(f"خطا: {e}")

# ==========================================
# تب سوم: پنل مدیریت و حذف متغیرها
# ==========================================
with tab3:
    st.subheader("⚙️ مدیریت متغیرهای پایگاه داده")
    st.markdown("در این بخش می‌توانید لیست متغیرهای موجود را مشاهده کرده و موارد دلخواه را به همراه تاریخچه‌های وابسته حذف کنید.")
    
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, series_code, title FROM series_registry ORDER BY id")
        series_list = cursor.fetchall()
        conn.close()
        
        if series_list:
            df_series = pd.DataFrame(series_list, columns=["ID", "Series Code", "Title"])
            st.dataframe(df_series, use_container_width=True)
            
            st.markdown("---")
            st.write("### حذف متغیر")
            selected_id_to_delete = st.selectbox("انتخاب ID متغیر جهت حذف:", [s[0] for s in series_list])
            
            selected_info = next((s for s in series_list if s[0] == selected_id_to_delete), None)
            if selected_info:
                st.warning(f"⚠️ شما در حال انتخاب متغیر **{selected_info[1]} ({selected_info[2]})** با شناسه ID [{selected_info[0]}] هستید.")
                
                if st.button("🗑️ حذف کامل این متغیر و داده‌های وابسته"):
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        sid = selected_id_to_delete
                        
                        cursor.execute("DELETE FROM standardized_observation_inputs WHERE standardized_observation_id IN (SELECT id FROM standardized_observations WHERE series_id = ?)", (sid,))
                        cursor.execute("DELETE FROM standardized_observations WHERE series_id = ?", (sid,))
                        cursor.execute("DELETE_RAW",) # (handled via standard sql below)
                        cursor.execute("DELETE FROM raw_observation_runs WHERE raw_observation_id IN (SELECT id FROM raw_observations WHERE series_id = ?)", (sid,))
                        cursor.execute("DELETE FROM raw_observations WHERE series_id = ?", (sid,))
                        cursor.execute("DELETE FROM collection_run_series WHERE series_id = ?", (sid,))
                        cursor.execute("DELETE FROM collection_logs WHERE series_id = ?", (sid,))
                        cursor.execute("DELETE FROM series_registry WHERE id = ?", (sid,))
                        
                        conn.commit()
                        conn.close()
                        st.success(f"✅ متغیر با شناسه [{sid}] با موفقیت و به‌طور کامل حذف شد. صفحه را رفرش کنید.")
                    except Exception as e:
                        st.error(f"❌ خطا در عملیات حذف: {e}")
        else:
            st.info("هیچ متغیری در دیتابیس ثبت نشده است.")
    else:
        st.warning("دیتابیس در دسترس نیست.")
