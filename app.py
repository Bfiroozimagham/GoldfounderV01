import streamlit as st
import sqlite3
import pandas as pd
import zipfile
import os

st.set_page_config(page_title="Gold Data Pipeline", page_icon="🪙", layout="wide")

st.title("🪙 سامانه خودکار جمع‌آوری و مدیریت داده‌های طلا")

ZIP_PATH = "economic_data.zip"
DB_PATH = "economic_data.db"

# استخراج فایل زیپ اگر وجود دارد
if os.path.exists(ZIP_PATH):
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(".")
        st.success(f"فایل زیپ با موفقیت استخراج شد. محتویات داخل زیپ: {zip_ref.namelist()}")
else:
    st.error(f"❌ فایل {ZIP_PATH} در مخزن گیت‌هاب پیدا نشد! لطفاً بررسی کنید که آیا فایل دقیقاً با همین نام آپلود شده است.")

# نمایش فایل‌های موجود در پوشه برای بررسی
st.write("فایل‌های موجود در پوشه سرور:", os.listdir("."))

# بررسی وجود فایل دیتابیس
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

            # دکمه دانلود اکسل
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
    st.warning("⚠️ فایل دیتابیس economic_data.db پس از استخراج یافت نشد.")
