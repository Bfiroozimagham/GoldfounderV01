import streamlit as st
import sqlite3
import pandas as pd
import datetime

# تنظیمات صفحه وب
st.set_page_config(page_title="Gold Data Pipeline", page_icon="🪙", layout="wide")

st.title("🪙 سامانه خودکار جمع‌آوری و مدیریت داده‌های طلا")
st.markdown("این سامانه آخرین اطلاعات بازار و متغیرهای کلان اقتصادی را مدیریت و نمایش می‌دهد.")

# مسیر دیتابیس (چون فایل دیتابیس را کنار این کد آپلود می‌کنیم)
DB_PATH = "economic_data.db"

# تابع برای خواندن داده‌ها از دیتابیس
@st.cache_data(ttl=60)
def load_data():
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
        df['observation_date'] = pd.to_datetime(df['observation_date'])
        return df
    except Exception as e:
        st.error(f"خطا در اتصال به دیتابیس: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # بخش ۱: آخرین مقادیر
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
        processed_data = output.getvalue()
        return processed_data

    excel_data = convert_df_to_excel(df)
    st.download_button(
        label="📥 دانلود کل تاریخچه داده‌ها به صورت اکسل",
        data=excel_data,
        file_name="economic_data_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # بخش ۲: نمودارهای روند
    st.subheader("📈 نمودارهای روند تاریخی")
    series_codes = df['series_code'].unique()
    selected_series = st.selectbox("انتخاب متغیر برای مشاهده نمودار:", series_codes)
    
    if selected_series:
        series_df = df[df['series_code'] == selected_series]
        st.line_chart(series_df.set_index('observation_date')['value'])
else:
    st.warning("هنوز دیتابیسی یافت نشد یا داده‌ای وجود ندارد. لطفاً فایل دیتابیس را آپلود کنید.")
