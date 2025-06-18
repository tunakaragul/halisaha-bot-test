#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏟️ Halısaha Rezervasyon Bot - FULL WORKING VERSION
25 Haziran 2025 17:00 hedefli test
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

def parse_turkish_date(date_str):
    """Türkçe tarihi datetime objesine çevir"""
    try:
        month_tr_to_num = {
            "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4,
            "Mayıs": 5, "Haziran": 6, "Temmuz": 7, "Ağustos": 8,
            "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12
        }
        
        parts = date_str.strip().split()
        day = int(parts[0])
        month = month_tr_to_num[parts[1]]
        year = int(parts[2])
        
        return datetime(year, month, day)
    except Exception as e:
        logging.error(f"❌ Tarih parse hatası: {e}")
        return None

def is_date_in_range(target_date_str, date_range_str):
    """Hedef tarihin aralık içinde olup olmadığını kontrol et"""
    try:
        logging.info(f"🔍 Tarih kontrolü: '{target_date_str}' in '{date_range_str}'")
        
        # Basit string kontrolü önce
        if target_date_str in date_range_str:
            logging.info("✅ String eşleşmesi bulundu!")
            return True
        
        # Aralık parse et
        if " - " not in date_range_str:
            # Tek tarih
            target_dt = parse_turkish_date(target_date_str)
            range_dt = parse_turkish_date(date_range_str)
            result = target_dt == range_dt if target_dt and range_dt else False
            logging.info(f"📅 Tek tarih karşılaştırması: {result}")
            return result
        
        # Aralık var
        range_parts = date_range_str.split(" - ")
        start_date_str = range_parts[0].strip()
        end_date_str = range_parts[1].strip()
        
        logging.info(f"📅 Aralık: '{start_date_str}' - '{end_date_str}'")
        
        target_dt = parse_turkish_date(target_date_str)
        start_dt = parse_turkish_date(start_date_str)
        end_dt = parse_turkish_date(end_date_str)
        
        if target_dt and start_dt and end_dt:
            result = start_dt <= target_dt <= end_dt
            logging.info(f"📅 Aralık kontrolü: {result} ({start_dt.strftime('%d.%m')} <= {target_dt.strftime('%d.%m')} <= {end_dt.strftime('%d.%m')})")
            return result
        
        logging.error("❌ Tarih parse edilemedi")
        return False
        
    except Exception as e:
        logging.error(f"❌ Aralık kontrol hatası: {e}")
        return False

def get_navigation_direction(target_date_str, current_range_str):
    """Hangi yöne navigate edilecegini belirle"""
    try:
        if " - " not in current_range_str:
            # Tek tarih - basit karşılaştırma
            target_dt = parse_turkish_date(target_date_str)
            current_dt = parse_turkish_date(current_range_str)
            if target_dt and current_dt:
                if target_dt > current_dt:
                    return "next"
                elif target_dt < current_dt:
                    return "prev"
                else:
                    return "found"
            return "next"  # default
        
        # Aralık var
        range_parts = current_range_str.split(" - ")
        start_date_str = range_parts[0].strip()
        end_date_str = range_parts[1].strip()
        
        target_dt = parse_turkish_date(target_date_str)
        start_dt = parse_turkish_date(start_date_str)
        end_dt = parse_turkish_date(end_date_str)
        
        if target_dt and start_dt and end_dt:
            if target_dt < start_dt:
                logging.info(f"📍 Hedef ({target_dt.strftime('%d.%m')}) aralık başından ({start_dt.strftime('%d.%m')}) önce -> ÖNCEKİ")
                return "prev"
            elif target_dt > end_dt:
                logging.info(f"📍 Hedef ({target_dt.strftime('%d.%m')}) aralık sonundan ({end_dt.strftime('%d.%m')}) sonra -> SONRAKİ")
                return "next"
            else:
                logging.info(f"📍 Hedef ({target_dt.strftime('%d.%m')}) aralık içinde ({start_dt.strftime('%d.%m')}-{end_dt.strftime('%d.%m')}) -> BULUNDU")
                return "found"
        
        # Default fallback
        return "next"
        
    except Exception as e:
        logging.error(f"❌ Yön belirleme hatası: {e}")
        return "next"

class WorkingHalisahaBot:
    def __init__(self):
        self.username = os.environ.get('HALISAHA_USERNAME')
        self.password = os.environ.get('HALISAHA_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Kullanıcı bilgileri eksik!")
        
        self.base_url = "https://spor.kadikoy.bel.tr"
        self.target_facility_url = "https://spor.kadikoy.bel.tr/spor-salonu/kalamis-spor?activityCategories=2"
        
        # HEDEF: 25 Haziran 2025 17:00
        self.target_date = "25 Haziran 2025"
        self.target_hours = ["17:00/18:00", "18:00/19:00", "16:00/17:00"]  # Backup saatler
        
        self.driver = None
        
        logging.info(f"🎯 WORKING Bot hazır - Hedef: {self.target_date} 17:00")
    
    def setup_driver(self):
        """Driver setup - GitHub Actions optimized"""
        try:
            logging.info("🔧 Driver setup başladı")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(15)
            self.driver.implicitly_wait(3)
            
            logging.info("✅ Driver hazır")
            return True
            
        except Exception as e:
            logging.error(f"❌ Driver setup hatası: {str(e)}")
            return False
    
    def login(self):
        """Login işlemi"""
        try:
            logging.info("🔐 Giriş işlemi başlatılıyor...")
            
            self.driver.get(f"{self.base_url}/giris")
            
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            
            login_button = self.driver.find_element(By.ID, "btnLoginSubmit")
            self.driver.execute_script("arguments[0].click();", login_button)
            
            time.sleep(3)
            
            if "giris" not in self.driver.current_url:
                logging.info("✅ Giriş başarılı")
                return True
            else:
                logging.error("❌ Giriş başarısız")
                return False
                
        except Exception as e:
            logging.error(f"❌ Login hatası: {str(e)}")
            return False
    
    def navigate_to_facility(self):
        """Halısaha sayfasına git"""
        try:
            logging.info("🏟️ Halısaha sayfasına yönlendiriliyor...")
            
            self.driver.get(self.target_facility_url)
            time.sleep(5)  # Sayfa yüklenmesi için
            
            logging.info(f"✅ Halısaha sayfası: {self.driver.current_url}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Sayfa yönlendirme hatası: {str(e)}")
            return False
    
    def navigate_to_target_date(self):
        """Hedef tarihe git - Working version"""
        try:
            logging.info(f"🗓️ Hedef tarihe navigasyon: {self.target_date}")
            
            # Alert handling
            try:
                alert = self.driver.switch_to.alert
                alert.dismiss()
                logging.info("🚨 Alert kapatıldı")
            except:
                pass
            
            # Mevcut tarihi al
            current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
            logging.info(f"📅 Başlangıç tarih aralığı: {current_date}")
            
            max_attempts = 10
            current_attempt = 0
            
            while current_attempt < max_attempts:
                try:
                    current_date = self.driver.find_element(By.CLASS_NAME, "yonlendirme-info").text
                    logging.info(f"📍 Deneme {current_attempt + 1}: Mevcut tarih aralığı: '{current_date}'")
                    
                    if not current_date:
                        logging.warning("⚠️ Tarih bilgisi yok, bekleniyor...")
                        time.sleep(2)
                        current_attempt += 1
                        continue
                    
                    # Hedef tarih kontrolü
                    if is_date_in_range(self.target_date, current_date):
                        logging.info("✅ HEDEF TARİH BULUNDU! Aralık içinde.")
                        return True
                    
                    # Hangi yöne gidileceğini belirle
                    direction = get_navigation_direction(self.target_date, current_date)
                    
                    if direction == "found":
                        logging.info("✅ HEDEF TARİH BULUNDU! (Parse kontrolü)")
                        return True
                    elif direction == "prev":
                        logging.info("⬅️ Önceki haftaya geçiliyor...")
                        try:
                            onceki_hafta_button = self.driver.find_element(By.ID, "area-onceki-hafta")
                            self.driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", onceki_hafta_button)
                        except Exception as btn_error:
                            logging.error(f"❌ Önceki hafta butonu hatası: {btn_error}")
                            break
                    elif direction == "next":
                        logging.info("➡️ Sonraki haftaya geçiliyor...")
                        try:
                            sonraki_hafta_button = self.driver.find_element(By.ID, "area-sonraki-hafta")
                            self.driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", sonraki_hafta_button)
                        except Exception as btn_error:
                            logging.error(f"❌ Sonraki hafta butonu hatası: {btn_error}")
                            break
                    
                    time.sleep(3)  # Sayfa yüklenmesi için bekle
                    current_attempt += 1
                    
                except Exception as nav_error:
                    logging.error(f"❌ Navigasyon hatası: {nav_error}")
                    current_attempt += 1
                    time.sleep(2)
            
            if current_attempt >= max_attempts:
                logging.error(f"❌ {max_attempts} denemede hedef tarihe ulaşılamadı")
                return False
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Tarih navigasyon genel hatası: {str(e)}")
            return False
    
    def find_and_reserve_slot(self):
        """Slot bul ve rezerve et - Working version"""
        try:
            logging.info(f"🎯 Hedef tarihte, slotlar aranıyor...")
            time.sleep(3)
            
            all_slots = self.driver.find_elements(By.CSS_SELECTOR, "div.lesson.active")
            logging.info(f"📊 Toplam {len(all_slots)} aktif slot bulundu")
            
            # Tüm slotları listele (debug için)
            logging.info("📋 Mevcut slotlar:")
            for i, slot in enumerate(all_slots[:10]):  # İlk 10 slot
                try:
                    date = slot.get_attribute("data-dateformatted")
                    hour = slot.get_attribute("data-hour")
                    logging.info(f"   {i+1:2d}. {date} - {hour}")
                except:
                    logging.info(f"   {i+1:2d}. Slot okunamadı")
            
            # Hedef slotu ara
            logging.info(f"🔍 Hedef slot aranıyor: {self.target_date}")
            target_slot = None
            found_hour = None
            
            for test_hour in self.target_hours:
                logging.info(f"   🕐 Aranan saat: {test_hour}")
                for slot in all_slots:
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        hour = slot.get_attribute("data-hour")
                        
                        if date == self.target_date and hour == test_hour:
                            target_slot = slot
                            found_hour = hour
                            logging.info(f"🎯 HEDEF SLOT BULUNDU: {date} - {hour}")
                            break
                    except:
                        continue
                
                if target_slot:
                    break
            
            if not target_slot:
                logging.error(f"❌ Hedef slot bulunamadı: {self.target_date} {self.target_hours}")
                
                # Sadece hedef tarih slotlarını göster
                logging.info(f"🔍 {self.target_date} tarihli tüm slotlar:")
                for i, slot in enumerate(all_slots):
                    try:
                        date = slot.get_attribute("data-dateformatted")
                        hour = slot.get_attribute("data-hour")
                        if date == self.target_date:
                            logging.info(f"   📅 {self.target_date} slot: {hour}")
                    except:
                        continue
                
                return False
            
            # REZERVASYON İŞLEMİ
            logging.info(f"✅ Slot bulundu, rezervasyon işlemi başlatılıyor...")
            logging.info(f"📍 Slot detayı: {self.target_date} - {found_hour}")
            
            # Slot seçimi
            self.driver.execute_script("arguments[0].click();", target_slot)
            logging.info("✅ Slot tıklandı")
            
            # Pop-up'ın yüklenmesi için bekle
            time.sleep(3)
            
            try:
                # Pop-up'ın yüklenmesini bekle
                wait = WebDriverWait(self.driver, 10)
                popup = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "bootbox")))
                logging.info("✅ Pop-up yüklendi")
                
                # "Rezerve Et" seçeneğini bul
                rezerve_radio = None
                selectors = [
                    "input[value='basvuru-yap']",
                    "input[name='basvuru-1']",
                    "div.hover-class input[type='radio']"
                ]
                
                for selector in selectors:
                    try:
                        rezerve_radio = popup.find_element(By.CSS_SELECTOR, selector)
                        if rezerve_radio:
                            logging.info(f"✅ Rezerve Et seçeneği bulundu: {selector}")
                            break
                    except:
                        continue
                
                if rezerve_radio:
                    self.driver.execute_script("arguments[0].click();", rezerve_radio)
                    logging.info("✅ Rezerve Et seçeneği seçildi")
                    
                    # Devam butonunu bul ve tıkla
                    devam_button = popup.find_element(By.CSS_SELECTOR, "button.btn.btn-blue.devam-et")
                    self.driver.execute_script("arguments[0].click();", devam_button)
                    logging.info("✅ Devam butonuna tıklandı")
                    
                    # İkinci pop-up için bekle
                    time.sleep(2)
                    
                    # Rezervasyon kuralları checkbox'ını bul
                    rules_checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    self.driver.execute_script("arguments[0].click();", rules_checkbox)
                    logging.info("✅ Rezervasyon kuralları kabul edildi")
                    
                    # Evet butonunu bul ve tıkla
                    try:
                        # JavaScript ile tıklama
                        self.driver.execute_script("""
                            var buttons = document.querySelectorAll('button.btn.btn-blue');
                            for(var i=0; i<buttons.length; i++) {
                                if(buttons[i].textContent.trim() === 'Evet') {
                                    buttons[i].click();
                                    return true;
                                }
                            }
                        """)
                        logging.info("✅ JavaScript ile Evet butonuna tıklandı")
                        
                        # Tıklama sonrası bekle
                        time.sleep(5)
                        
                    except Exception as e:
                        logging.error(f"❌ Evet butonuna tıklarken hata: {str(e)}")
                    
                    # Rezervasyon kontrolü
                    time.sleep(2)
                    success = self.check_reservation_success(found_hour)
                    
                    if success:
                        logging.info("🎉 ✅ REZERVASYON BAŞARIYLA TAMAMLANDI!")
                        return True
                    else:
                        logging.error("❌ Rezervasyon tamamlanamadı veya doğrulanamadı!")
                        return False
                else:
                    logging.error("❌ Rezerve Et seçeneği bulunamadı")
                    return False
                    
            except Exception as popup_error:
                logging.error(f"❌ Pop-up işlemlerinde hata: {str(popup_error)}")
                return False
            
        except Exception as e:
            logging.error(f"❌ Slot bulma/rezervasyon genel hatası: {str(e)}")
            return False
    
    def check_reservation_success(self, target_hour):
        """Rezervasyonun başarılı olup olmadığını kontrol et"""
        try:
            logging.info(f"🔍 Rezervasyon kontrolü: {self.target_date} - {target_hour}")
            
            # Rezervasyonlarım sayfasına git
            self.driver.get(f"{self.base_url}/ClubMember/MyReservation.aspx")
            time.sleep(3)
            
            # Tablodaki tüm satırları bul
            rows = self.driver.find_elements(By.CSS_SELECTOR, "#AreaReservationTable tbody tr")
            logging.info(f"📊 Tabloda {len(rows)} satır bulundu")
            
            # Tarih formatını rezervasyon kontrol için düzenle
            check_date = "25.06.2025"  # 25 Haziran 2025
            check_hour = target_hour.replace("/", " - ") if target_hour else "17:00 - 18:00"
            
            logging.info(f"🔍 Aranan: {check_date} - {check_hour}")
            
            # Her satırı kontrol et
            for i, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 5:
                        date_cell = cells[2].text if len(cells) > 2 else ""
                        hour_cell = cells[3].text if len(cells) > 3 else ""
                        status = cells[4].text if len(cells) > 4 else ""
                        
                        logging.info(f"📋 Satır {i+1}: {date_cell} | {hour_cell} | {status}")
                        
                        # Tarih ve saat kontrolü
                        if (check_date in date_cell or "25.06" in date_cell or "25 Haziran" in date_cell) and "17:00" in hour_cell:
                            logging.info(f"✅ Rezervasyon bulundu:")
                            logging.info(f"   Tarih: {date_cell}")
                            logging.info(f"   Saat: {hour_cell}")
                            logging.info(f"   Durum: {status}")
                            
                            if "Ön Onaylı" in status or "Onaylı" in status:
                                return True
                except Exception as row_error:
                    logging.error(f"⚠️ Satır {i+1} okuma hatası: {str(row_error)}")
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"❌ Rezervasyon kontrolü hatası: {str(e)}")
            return False
    
    def send_email(self, subject, message):
        """Email gönder"""
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
    
    def run_working_test(self):
        """WORKING TEST ana fonksiyon"""
        start_time = time.time()
        
        try:
            logging.info("🚀 WORKING HALISAHA BOT başladı")
            logging.info(f"🎯 Hedef: {self.target_date} 17:00")
            logging.info("="*60)
            
            # 1. Driver setup
            if not self.setup_driver():
                raise Exception("Driver setup başarısız")
            
            # 2. Login
            if not self.login():
                raise Exception("Login başarısız")
            
            # 3. Halısaha sayfasına git
            if not self.navigate_to_facility():
                raise Exception("Sayfa yönlendirme başarısız")
            
            # 4. Hedef tarihe git
            if not self.navigate_to_target_date():
                raise Exception("Hedef tarih bulunamadı")
            
            # 5. Slot bul ve rezerve et
            if self.find_and_reserve_slot():
                elapsed_time = time.time() - start_time
                
                logging.info("🏆 WORKING BOT BAŞARILI!")
                logging.info(f"⏱️ Toplam süre: {elapsed_time:.0f} saniye")
                
                self.send_email(
                    "🏆 25 Haziran 17:00 REZERVASYON BAŞARILI!",
                    f"""🎉 WORKING HALISAHA BOT BAŞARILI!
                    
📅 Tarih: {self.target_date}
🕐 Saat: 17:00-18:00
⏱️ Süre: {elapsed_time:.0f} saniye
🏟️ Tesis: Kalamış Spor Tesisi
⚽ Alan: Halı Saha
✅ Durum: Ön Onaylı

🚀 Working bot mükemmel çalıştı!
Ana production'a hazır! 🎯"""
                )
            else:
                elapsed_time = time.time() - start_time
                
                logging.warning("❌ Slot bulunamadı veya rezerve edilemedi")
                
                self.send_email(
                    "📊 25 Haziran 17:00 Test Raporu",
                    f"""🔍 WORKING BOT TEST RAPORU
                    
📅 Tarih: {self.target_date}
🕐 Hedef Saat: 17:00-18:00
⏱️ Süre: {elapsed_time:.0f} saniye

✅ Driver: Çalışıyor
✅ Login: Başarılı
✅ Navigation: Çalışıyor
✅ Date Navigation: Çalışıyor
❌ Target Slot: 17:00 bulunamadı

25 Haziran 17:00 slot'u mevcut değil veya dolu.
Working bot logic'i çalışıyor! 📋"""
                )
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logging.error(f"WORKING BOT Ana hata ({elapsed_time:.0f}s): {str(e)}")
            self.send_email("❌ WORKING BOT Hatası", f"Hata ({elapsed_time:.0f}s): {str(e)}")
        
        finally:
            # Cleanup
            if self.driver:
                try:
                    logging.info(f"📍 Son URL: {self.driver.current_url}")
                    self.driver.save_screenshot("working_bot_result.png")
                    logging.info("📸 Ekran görüntüsü kaydedildi")
                except:
                    logging.warning("⚠️ Ekran görüntüsü kaydedilemedi")
                
                self.driver.quit()
                logging.info("🔒 Browser kapatıldı")

def main():
    logging.info("🏟️ WORKING Halısaha Bot")
    logging.info("🎯 Hedef: 25 Haziran 2025 (17:00-18:00)")
    logging.info("🔧 Base: Çalışan eski kod mantığı")
    logging.info("="*60)
    
    bot = WorkingHalisahaBot()
    bot.run_working_test()

if __name__ == "__main__":
    main()
