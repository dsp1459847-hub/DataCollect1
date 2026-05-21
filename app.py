import streamlit as st
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

st.set_page_config(page_title="Copy Checker", layout="wide")
st.title("🕵️ 'Copy' Check Tool - Single Shift Test")
st.write("Bhai, pehle sirf 1 shift ka data nikal kar screen par dekhte hain ki 'Copy' theek se ho raha hai ya nahi. Excel baad mein banayenge.")

# User se sirf ek shift ka naam puchenge
shift_name = st.text_input("Kisi ek Shift ka naam daaliye (Jaise: GALI DISAWAR MIX, ya OLD CITY):", "OLD CITY")

if st.button("Check Data (Copy Test Karo)"):
    with st.spinner(f"⏳ Site se '{shift_name}' ko copy karne ki koshish ho rahi hai..."):
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        try:
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            st.error("Driver load nahi hua. GitHub packages check karein.")
            st.stop()

        try:
            driver.get("https://satta-king-fast.com/chart.php")
            time.sleep(3)
            
            # Niche tak scroll karna taaki sab load ho jaye
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Record chart wale saare button nikalna
            buttons = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'record chart')]")
            
            target_btn = None
            # Sirf us button ko dhundhna jiske paas aapka daala hua naam hai
            for btn in buttons:
                try:
                    if shift_name.lower() in btn.find_element(By.XPATH, "..").text.lower():
                        target_btn = btn
                        break
                except:
                    pass
            
            if not target_btn:
                st.error(f"❌ '{shift_name}' naam ki shift site par nahi mili! Naam ki spelling check karein.")
            else:
                st.info("✅ Shift mil gayi! Ab uska 'Record Chart' button click kar raha hoon...")
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target_btn)
                
                # AJAX table load hone ka wait (5 second)
                time.sleep(5) 

                # Sabse niche wala table dhundhna jisme data aata hai
                tables = driver.find_elements(By.TAG_NAME, "table")
                copied_text = ""
                
                for table in reversed(tables):
                    if table.is_displayed():
                        # Agar us naye table ke andar ya upar shift ka naam hai
                        if shift_name.lower() in table.text.lower() or shift_name.lower() in table.find_element(By.XPATH, "..").text.lower():
                            copied_text = table.text # YAHAN ASLI COPY HO RAHA HAI
                            break
                
                if copied_text:
                    st.success("🎯 Data Copy Ho Gaya! Niche dekhiye bot ne kya copy kiya hai:")
                    st.text_area("Bot ne yeh padha hai:", copied_text, height=300)
                else:
                    st.error("❌ Button click hua, par site ne table hi khol kar nahi diya (Copy Fail!). Ho sakta hai site block kar rahi ho.")
                    
        except Exception as e:
            st.error(f"Error aaya: {e}")
        finally:
            driver.quit()
                      
