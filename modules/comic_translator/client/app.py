import streamlit as st
import requests
import io

# 服务端 API 地址
BACKEND_URL = 'http://8.134.219.231:8000'

st.set_page_config(page_title="漫画批量翻译", layout="wide")

st.title("📚 漫画批量翻译工具")
st.markdown("上传多张漫画图片，服务器将进行批量处理")

# --- 1. 目标语言选择组件 ---
# 定义目标语言及其对应的代码（假设后端需要的代码）
LANGUAGE_MAP = {
    "英语 (English)": "English",
    "中文 (Chinese)": "Chinese",
    "日语 (Japanese)": "Japanese",
    "韩语 (Korean)": "Korean",
    # 可以根据需要添加更多语言
}
default_lang_display = "中文 (Chinese)"

st.subheader("⚙️ 翻译设置")
selected_lang_display = st.selectbox(
    "选择目标翻译语言:",
    options=list(LANGUAGE_MAP.keys()),
    index=list(LANGUAGE_MAP.keys()).index(default_lang_display)
)

# 获取后端需要的语言代码
target_lang_code = LANGUAGE_MAP[selected_lang_display]
st.info(f"选定的目标语言代码为: **{target_lang_code}**，将作为参数传给服务器")

# --- 2. 文件上传组件 ---
st.subheader("🖼️ 图片上传")
uploaded_files = st.file_uploader( 
    "选择多张漫画图片 (JPG, PNG, WebP 等)", 
    type=['jpg', 'jpeg', 'png', 'webp'], 
    accept_multiple_files=True
)

if uploaded_files:
    st.subheader(f"已上传 {len(uploaded_files)} 张图片")

    # 1. 显示已上传的图片列表（可选，但通常有助于用户确认）
    files_data = []
    
    # 使用 st.expander 将图片列表折叠起来，避免占据太多空间
    # with st.expander("点击查看已上传的图片缩略图"):
    #     cols = st.columns(3)
        
    for i, file in enumerate(uploaded_files):
        # ⚠️ 在读取之前重置指针，确保从文件开头开始
        file.seek(0)
        
        # 将文件内容读取到内存 (bytes)
        file_bytes = file.read()
        
        # 将文件数据存储下来
        files_data.append({
            'name': file.name,
            'type': file.type,
            'bytes': file_bytes
        })
        
        # # 显示图片（可选）
        # with cols[i % 3]:
        #     st.image(file_bytes, caption=f"原始图片 {i+1}", use_column_width=True)

    # 2. 准备发送文件的字典
    files_to_send = {}
    
    # 从 files_data 中获取字节流并打包成字典
    # 约定：前端使用 image_file_0, image_file_1, ... 作为文件字段名
    for i, data in enumerate(files_data):
        # 键名格式为 'image_file_N'
        # (文件名, 文件字节流, Content-Type)
        files_to_send[f'image_file_{i}'] = (data['name'], data['bytes'], data['type'])

    # 3. 准备发送的数据 (Payload) 字典
    payload_data = {
        'target_lang': target_lang_code # 将目标语言代码包含在请求数据中
    }

    # 4. 发送按钮
    if st.button('开始批量处理'):
        with st.spinner('🚀 正在连接服务器进行批量处理...'):
            try:
                # 发送请求给后端服务器 同时发送文件 (files) 和其他数据 (data)
                response = requests.post(
                    BACKEND_URL, 
                    files=files_to_send, 
                    data=payload_data,
                    timeout=1000
                )
                
                # 检查响应
                if response.status_code == 200:

                    # 检查返回的内容是否是 ZIP 文件
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    if 'application/zip' in content_type:
                        st.success(f"🎉 批量处理成功！服务器返回了一个 ZIP 包")
                        
                        zip_bytes = response.content
                        
                        # 提供下载按钮
                        st.download_button(
                            label="⬇️ 批量下载处理结果 (ZIP 文件)",
                            data=zip_bytes,
                            file_name=f"comic_batch_translate_to_{target_lang_code}.zip",
                            mime="application/zip"
                        )
                        st.balloons()

                    else:
                        st.error("❌ 服务器返回了成功的状态码，但内容不是预期的 ZIP 文件")
                        st.write(f"Received Content Type: {content_type}")
                        st.text(response.text[:500] or "[响应体为空]")

                else:
                    # 打印错误详情
                    st.error(f"❌ 服务器处理失败: 状态码 {response.status_code}. 响应内容: {response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"❌ 连接服务器失败: 请检查 IP/端口是否正确，或服务器是否开启: {e}")

else:
    st.info("请上传一张或多张图片开始批量处理")