#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - TARGETED TEST VERSION
25 Haziran 17:00 slotunu hedefle
"""

import os
import sys
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from datetime import datetime, timedelta

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def is_target_date_in_week(target_date_str, week_range_str):
    """Hedef tarih bu hafta aralığında mı?"""
    try:
        if target_date_str in week_range_str:
            return True
        
        if " - " not in week_range_str:
            return False
        
        # "23 Haziran 2025 - 29 Haziran 2025" gibi format
        range_parts = week_range_str.split(" - ")
        start_str = range_parts[0].strip()
        end_str = range_parts[1].strip()
        
        # Basit kontrol: "25 Haziran 2025" in "23 Haziran 2025 - 29 Haziran 2025"
        return target_date_str in week_range_str
        
    except Exception as e:
        logging.error(f"Tarih kontrolü hatası: {str(e)}")
        return False

class TargetedTestBrowser:
    """25 Haziran 17:00 hedefli test browser"""
    def __init__(self, username, password, base_url, target_facility_url):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.target_facility_url = target_facility_url
        self.driver = None
        self.is_ready = False
        
        # HEDEF: 25 Haziran 17:00
        self.target_date = "25 Haziran 2025"
        self.target_hours = ["17:00/18:00", "17:00-18:00"]  # Her iki format da dene
        
    def quick_setup_and_login(self):
        """Hızlı setup"""
        try:
            logging.info("🔧 Targeted Test Browser setup başladı")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--window-size=800,600')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(10)
            self.driver.implicitly_wait(2)
            
            # Login
            self.driver.get(f"{self.base_url}/giris")
            
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            self.driver.execute_script(f"arguments[0].value = '{self.username}';", username_field)
            self.driver.execute_script(f"arguments[0].value = '{self.password}';", password_field)
            
            login_button = self.driver.find_element(By.ID, "btnLoginSubmit")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            time.sleep(2)
            
            if "giris" not in self.driver.current_url:
                self.driver.get(self.target_facility_url)
                time.sleep(2)
                
                self.is_ready = True
                logging.info("✅ Targeted Test Browser HAZIR!")
                return True
            else:
                logging.error("❌ Login başarısız")
                return False
                
        except Exception as e:
            logging.error(f"❌ Setup hatası: {str(e)}")
            return False
    
    def navigate_to_target_week(self):
        """25 Haziran'ın olduğu haftaya git - IMPROVED TIMING"""
        try:
            logging.info(f"🗓️ Hedef haftayı arıyor: {self.target_date}")
            
            # Alert handling
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()
                logging.info("🚨 Alert kapatıldı")
            except:
                pass
            
            # Sayfa refresh
            self.driver.refresh()
            time.sleep(2)  # 1→2 saniye - sayfa yüklenmesi için
            
            # Maksimum 5 hafta ileriye git
            for week_attempt in range(5):
                try:
                    # IMPROVED: Mevcut hafta aralığını oku - element'in yüklenmesini bekle
                    current_week_element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "yonlendirme-info"))
                    )
                    
                    # Element text'inin boş olmamasını bekle
                    current_week = ""
                    for text_wait in range(5):  # 5 kez dene
                        current_week = current_week_element.text.strip()
                        if current_week:  # Boş değilse
                            break
                        time.sleep(0.5)  # 0.5 saniye bekle ve tekrar dene
                    
                    logging.info(f"📅 Hafta #{week_attempt+1}: '{current_week}'")
                    
                    # Eğer hala boşsa, daha uzun bekle
                    if not current_week:
                        logging.warning(f"⚠️ Hafta metni boş, 2 saniye daha bekleniyor...")
                        time.sleep(2)
                        current_week = current_week_element.text.strip()
                        logging.info(f"📅 Hafta #{week_attempt+1} (retry): '{current_week}'")
                    
                    # Hedef tarih bu hafta aralığında mı?
                    if current_week and is_target_date_in_week(self.target_date, current_week):
                        logging.info(f"✅ HEDEF HAFTA BULUNDU! {current_week}")
                        return True
                    
                    # Değilse sonraki hafta - IMPROVED TIMING
                    logging.info(f"➡️ Sonraki haftaya geçiliyor...")
                    
                    # Önceki hafta bilgisini sakla (değişiklik kontrolü için)
                    previous_week = current_week
                    
                    next_week_button = self.driver.find_element(By.ID, "area-sonraki-hafta")
                    self.driver.execute_script("arguments[0].click();", next_week_button)
                    
                    # CRITICAL: Sayfa değişimini bekle
                    time.sleep(2)  # 1→2 saniye - sayfa yüklenmesi için
                    
                    # EXTRA: Tarih değişikliğini bekle
                    for change_wait in range(10):  # Maksimum 5 saniye bekle
                        try:
                            new_week_element = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info")
                            new_week = new_week_element.text.strip()
                            
                            if new_week and new_week != previous_week:
                                logging.info(f"✅ Hafta değişti: '{previous_week}' → '{new_week}'")
                                break
                            
                            time.sleep(0.5)  # 0.5 saniye bekle
                            
                        except:
                            time.sleep(0.5)
                    
                    if change_wait == 9:  # Değişim tespit edilemedi
                        logging.warning(f"⚠️ Hafta değişimi tespit edilemedi, devam ediliyor...")
                    
                except TimeoutException:
                    logging.error(f"❌ Hafta #{week_attempt+1} element timeout")
                    break
                except Exception as e:
                    logging.error(f"❌ Hafta #{week_attempt+1} navigasyon hatası: {str(e)}")
                    break
            
            logging.error(f"❌ 5 haftada hedef tarih bulunamadı: {self.target_date}")
            
            # FINAL DEBUG: Son durumu göster
            try:
                final_week_element = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info")
                final_week = final_week_element.text.strip()
                logging.info(f"🔍 Final hafta durumu: '{final_week}'")
            except:
                logging.error(f"❌ Final hafta durumu okunamadı")
            
            return False
        
    except Exception as e:
        logging.error(f"❌ Hafta navigasyon genel hatası: {str(e)}")
        return False
    
    def find_and_reserve_target_slot(self):
        """25 Haziran 17:00 slotunu bul ve rezerve et"""
        try:
            logging.info(f"🎯 Hedef slot aranıyor: {self.target_date} {self.target_hours}")
            
            # Tüm slotları bul
            all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div.lesson.active")
            logging.info(f"📊 Toplam aktif slot: {len(all_slots)}")
            
            if len(all_slots) == 0:
                logging.warning(f"⚠️ HİÇ AKTİF SLOT YOK!")
                
                # Alternatif selectors dene
                alt_selectors = ["div.lesson", ".lesson", "div[data-hour]"]
                for selector in alt_selectors:
                    try:
                        alt_slots = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        logging.info(f"🔍 '{selector}': {len(alt_slots)} element")
                        if len(alt_slots) > 0:
                            all_slots = alt_slots
                            break
                    except:
                        pass
            
            # Hedef slotu ara
            target_slot = None
            
            for i, slot in enumerate(all_slots):
                try:
                    date = slot.get_attribute("data-dateformatted") or ""
                    slot_hour = slot.get_attribute("data-hour") or ""
                    slot_text = slot.text.strip() or ""
                    
                    # Debug: İlk 10 slotu göster
                    if i < 10:
                        logging.info(f"  📍 Slot #{i+1}: Tarih='{date}' Saat='{slot_hour}' Text='{slot_text}'")
                    
                    # Hedef slot kontrolü
                    if date == self.target_date and slot_hour in self.target_hours:
                        target_slot = slot
                        logging.info(f"🎯 HEDEF SLOT BULUNDU! Slot #{i+1}: {date} - {slot_hour}")
                        break
                        
                except Exception as e:
                    logging.error(f"❌ Slot #{i+1} okuma hatası: {str(e)}")
                    continue
            
            if not target_slot:
                logging.error(f"❌ HEDEF SLOT BULUNAMADI: {self.target_date} {self.target_hours}")
                
                # Sadece 25 Haziran slotlarını göster
                logging.info(f"🔍 25 Haziran slotları aranıyor...")
                for i, slot in enumerate(all_slots):
                    try:
                        date = slot.get_attribute("data-dateformatted") or ""
                        slot_hour = slot.get_attribute("data-hour") or ""
                        
                        if "25 Haziran" in date:
                            logging.info(f"  📅 25 Haziran slot: Saat='{slot_hour}'")
                    except:
                        continue
                
                return False
            
            # HEDEF SLOT REZERVASYONU
            logging.info(f"💥 Hedef slot rezerve ediliyor...")
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", target_slot)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", target_slot)
            
            # Popup bekle ve işle
            try:
                popup = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "bootbox"))
                )
                logging.info(f"✅ Rezervasyon popup'ı açıldı")
                
                # Rezerve radio seç
                rezerve_radio = popup.find_element(By.CSS_SELECTOR, "input[value='basvuru-yap']")
                self.driver.execute_script("arguments[0].click();", rezerve_radio)
                logging.info(f"✅ Rezerve radio seçildi")
                
                # Devam butonu
                devam_button = popup.find_element(By.CSS_SELECTOR, "button.btn.btn-blue.devam-et")
                self.driver.execute_script("arguments[0].click();", devam_button)
                logging.info(f"✅ Devam butonu tıklandı")
                
                time.sleep(1)
                
                # Rules checkbox
                rules_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                self.driver.execute_script("arguments[0].click();", rules_checkbox)
                logging.info(f"✅ Rules checkbox işaretlendi")
                
                # Final Evet butonu
                self.driver.execute_script("""
                    var buttons = document.querySelectorAll('button.btn.btn-blue');
                    for(var i=0; i<buttons.length; i++) {
                        if(buttons[i].textContent.trim() === 'Evet') {
                            buttons[i].click();
                            return true;
                        }
                    }
                """)
                logging.info(f"✅ Final 'Evet' butonu tıklandı")
                
                time.sleep(2)
                
                # Başarı kontrolü
                success = self.check_reservation_success()
                
                if success:
                    logging.info(f"🏆 REZERVASYON BAŞARILI! {self.target_date} 17:00")
                    return True
                else:
                    logging.warning(f"❌ Rezervasyon kontrol başarısız")
                    return False
                
            except TimeoutException:
                logging.error(f"❌ Popup timeout")
                return False
            except Exception as e:
                logging.error(f"❌ Rezervasyon işlem hatası: {str(e)}")
                return False
            
        except Exception as e:
            logging.error(f"❌ Slot bulma genel hatası: {str(e)}")
            return False
    
    def check_reservation_success(self):
        """Rezervasyon başarı kontrolü"""
        try:
            self.driver.get(f"{self.base_url}/ClubMember/MyReservation.aspx")
            time.sleep(2)
            
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#AreaReservationTable tbody tr")
            logging.info(f"📋 Rezervasyon tablosunda {len(rows)} satır bulundu")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        date_cell = cells[2].text if len(cells) > 2 else ""
                        hour_cell = cells[3].text if len(cells) > 3 else ""
                        status_cell = cells[4].text if len(cells) > 4 else ""
                        
                        logging.info(f"  📋 Satır #{i+1}: Tarih='{date_cell}' Saat='{hour_cell}' Durum='{status_cell}'")
                        
                        # 25 Haziran ve 17:00 kontrolü
                        if ("25 Haziran" in date_cell or "25.06" in date_cell) and ("17:00" in hour_cell):
                            if "Ön Onaylı" in status_cell or "Onaylı" in status_cell:
                                logging.info(f"🏆 BAŞARILI REZERVASYON DOĞRULANDI!")
                                return True
                                
                except Exception as e:
                    logging.error(f"❌ Satır #{i+1} okuma hatası: {str(e)}")
                    continue
            
            logging.warning(f"❌ Hedef rezervasyon tabloda bulunamadı")
            return False
            
        except Exception as e:
            logging.error(f"❌ Başarı kontrol hatası: {str(e)}")
            return False
    
    def cleanup(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

class TargetedTestBot:
    def __init__(self):
        self.username = os.environ.get('HALISAHA_USERNAME')
        self.password = os.environ.get('HALISAHA_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Kullanıcı bilgileri eksik!")
        
        self.base_url = "https://spor.kadikoy.bel.tr"
        self.target_facility_url = "https://spor.kadikoy.bel.tr/spor-salonu/kalamis-spor?activityCategories=2"
        
        logging.info(f"🎯 TARGETED TEST Bot hazır - Hedef: 25 Haziran 17:00")
    
    def send_email(self, subject, message):
        try:
            email = os.environ.get('NOTIFICATION_EMAIL')
            password = os.environ.get('EMAIL_PASSWORD')
            
            if not email or not password:
                logging.info("E-posta bilgileri yok, atlanıyor")
                return
            
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(email, password)
            server.send_message(msg)
            server.quit()
            
            logging.info(f"📧 E-posta gönderildi: {subject}")
        except Exception as e:
            logging.error(f"E-posta hatası: {str(e)}")
    
    def run_targeted_test(self):
        """TARGETED TEST ana fonksiyon"""
        browser = None
        
        try:
            logging.info(f"🚀 TARGETED TEST başladı - 25 Haziran 17:00 hedefi")
            
            # Browser setup
            browser = TargetedTestBrowser(
                self.username, self.password, 
                self.base_url, self.target_facility_url
            )
            
            if not browser.quick_setup_and_login():
                logging.error("❌ Browser setup başarısız!")
                self.send_email("❌ TARGETED TEST Hatası", "Browser setup başarısız!")
                return
            
            # Hedef haftaya git
            if not browser.navigate_to_target_week():
                logging.error("❌ Hedef hafta bulunamadı!")
                self.send_email("❌ TARGETED TEST Hatası", "25 Haziran haftası bulunamadı!")
                return
            
            # Hedef slotu bul ve rezerve et
            if browser.find_and_reserve_target_slot():
                logging.info(f"🏆 TARGETED TEST BAŞARILI!")
                
                self.send_email(
                    f"🏆 TARGETED TEST BAŞARILI!",
                    f"""🎯 25 Haziran 17:00 REZERVASYON BAŞARILI!
                    
✅ Browser: Çalışıyor
✅ Login: Başarılı  
✅ Week Navigation: Çalışıyor
✅ Slot Detection: Çalışıyor
✅ Reservation: 25 Haziran 17:00 BAŞARILI!

Targeted test mükemmel çalıştı! 🚀
Ana bot için hazır! 🎯"""
                )
            else:
                logging.warning(f"❌ TARGETED TEST - Hedef slot rezerve edilemedi")
                
                self.send_email(
                    f"📊 TARGETED TEST Raporu",
                    f"""🔍 TARGETED TEST RAPORU
                    
✅ Browser: Çalışıyor
✅ Login: Başarılı
✅ Week Navigation: Çalışıyor
❌ Target Slot: 25 Haziran 17:00 bulunamadı/rezerve edilemedi

25 Haziran 17:00 slot'u mevcut değil veya dolu.
Debug log'larını incele! 📋"""
                )
            
        except Exception as e:
            logging.error(f"TARGETED TEST Ana hata: {str(e)}")
            self.send_email("❌ TARGETED TEST Hatası", f"Hata: {str(e)}")
        
        finally:
            if browser:
                browser.cleanup()

def main():
    bot = TargetedTestBot()
    bot.run_targeted_test()

if __name__ == "__main__":
    main()
