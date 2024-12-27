import phonenumbers
from phonenumbers import carrier, timezone
import requests
import json
import sqlite3
from datetime import datetime
import os

class PhoneNumberAnalyzer:
    def __init__(self):
        self.initialize_database()
        self.apis = {
            'numverify': {
                'url': 'http://apilayer.net/api/validate',
                'key': 'YOUR_NUMVERIFY_KEY'
            },
            'veriphone': {
                'url': 'https://api.veriphone.io/v2/verify',
                'key': 'YOUR_VERIPHONE_KEY'
            },
            'phoneapis': {
                'url': 'https://phoneapis.com/api/v2/verify',
                'key': 'YOUR_PHONEAPIS_KEY'
            }
        }
        
        #database prefix untuk provider di indonesia
        self.provider_prefixes = {
            '811': 'Telkomsel', '812': 'Telkomsel', '813': 'Telkomsel', '821': 'Telkomsel', '822': 'Telkomsel', '823': 'Telkomsel',
            '851': 'Telkomsel', '852': 'Telkomsel', '853': 'Telkomsel',
            '814': 'Indosat', '815': 'Indosat', '816': 'Indosat', '855': 'Indosat', '856': 'Indosat', '857': 'Indosat', '858': 'Indosat',
            '817': 'XL', '818': 'XL', '819': 'XL', '859': 'XL', '877': 'XL', '878': 'XL',
            '838': 'AXIS', '831': 'AXIS', '832': 'AXIS', '833': 'AXIS',
            '895': 'Three', '896': 'Three', '897': 'Three', '898': 'Three', '899': 'Three',
            '881': 'Smart', '882': 'Smart', '883': 'Smart', '884': 'Smart', '885': 'Smart', '886': 'Smart', '887': 'Smart', '888': 'Smart', '889': 'Smart'
        }
        
        # database region/kota  untuk indonesia
        self.region_prefixes = {
            '21': 'Jakarta',
            '22': 'Bandung',
            '24': 'Semarang',
            '31': 'Surabaya',
            '61': 'Medan',
            '62': 'Sumatra',
            '63': 'Kalimantan',
            '65': 'Kalimantan Timur',
            '67': 'Maluku',
            '71': 'Sulawesi',
            '73': 'Sulawesi Selatan',
            '81': 'Papua'
        }

    def initialize_database(self):
        conn = sqlite3.connect('phone_analysis.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS analysis_history
                    (phone_number TEXT, timestamp TEXT, provider TEXT, 
                    location TEXT, valid INTEGER, type TEXT, 
                    additional_info TEXT)''')
        conn.commit()
        conn.close()

    def get_detailed_provider_info(self, prefix):
        prefix_3 = prefix[:3]
        prefix_4 = prefix[:4]
        
        provider_info = {
            'provider_name': self.provider_prefixes.get(prefix_3, 'Unknown'),
            'network_type': 'GSM',
            'provider_details': {}
        }
        
        # detail porvider
        provider_details = {
            'Telkomsel': {
                'full_name': 'PT Telekomunikasi Selular',
                'website': 'www.telkomsel.com',
                'customer_service': '188',
                'network_tech': ['2G', '3G', '4G', '5G'],
                'founded': 1995,
                'market_share': '46%',
                'parent_company': 'Telkom Indonesia & Singtel'
            },
            'Indosat': {
                'full_name': 'PT Indosat Ooredoo Hutchison',
                'website': 'www.indosatooredoo.com',
                'customer_service': '185',
                'network_tech': ['2G', '3G', '4G'],
                'founded': 1967,
                'market_share': '16%',
                'parent_company': 'Ooredoo & CK Hutchison'
            },
            'XL': {
                'full_name': 'PT XL Axiata',
                'website': 'www.xl.co.id',
                'customer_service': '817',
                'network_tech': ['2G', '3G', '4G'],
                'founded': 1989,
                'market_share': '14%',
                'parent_company': 'Axiata Group'
            },
            'AXIS': {
                'full_name': 'PT AXIS Telekom Indonesia (Now XL Axiata)',
                'website': 'www.axis.co.id',
                'customer_service': '838',
                'network_tech': ['3G', '4G'],
                'founded': 2005,
                'market_share': '5%',
                'parent_company': 'XL Axiata'
            },
            'Three': {
                'full_name': 'PT Hutchison 3 Indonesia',
                'website': 'www.three.co.id',
                'customer_service': '123',
                'network_tech': ['3G', '4G'],
                'founded': 2007,
                'market_share': '12%',
                'parent_company': 'CK Hutchison Holdings'
            }
        }
        
        if provider_info['provider_name'] in provider_details:
            provider_info['provider_details'] = provider_details[provider_info['provider_name']]
        
        return provider_info

    def get_region_info(self, prefix):
        for region_prefix, region in self.region_prefixes.items():
            if prefix.startswith(region_prefix):
                return region
        return 'Unknown Region'

    def get_number_category(self, number):
        if number.startswith('0800'):
            return 'Toll-Free'
        elif number.startswith('0899'):
            return 'Premium Rate'
        elif number.startswith('0878'):
            return 'Personal Number'
        else:
            return 'Regular Mobile'

    def analyze_phone_number(self, phone_number):
        try:
            cleaned_number = ''.join(filter(str.isdigit, phone_number))
            if cleaned_number.startswith('62'):
                cleaned_number = '0' + cleaned_number[2:]
            
            parsed_number = phonenumbers.parse(phone_number)
            
            if not phonenumbers.is_valid_number(parsed_number):
                return {"error": "Nomor telepon tidak valid"}

            # informasi dasar
            prefix = cleaned_number[1:4]  # Ambil 3 digit setelah '0'
            provider_info = self.get_detailed_provider_info(prefix)
            
            result = {
                "nomor": {
                    "original": phone_number,
                    "format_nasional": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL),
                    "format_internasional": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                    "format_e164": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164),
                    "prefix": prefix,
                    "nomor_bersih": cleaned_number,
                    "kategori": self.get_number_category(cleaned_number)
                },
                
                "validasi": {
                    "valid": phonenumbers.is_valid_number(parsed_number),
                    "kemungkinan": phonenumbers.is_possible_number(parsed_number),
                    "tipe_nomor": self.get_number_type(parsed_number),
                    "format_valid": True
                },
                
                "provider": {
                    "nama": provider_info['provider_name'],
                    "network_type": provider_info['network_type'],
                    "detail": provider_info['provider_details']
                },
                
                "lokasi": {
                    "negara": "Indonesia",
                    "kode_negara": "+62",
                    "region": self.get_region_info(prefix),
                    "zona_waktu": list(timezone.time_zones_for_number(parsed_number)),
                    "carrier_region": carrier.region_code_for_number(parsed_number)
                },
                
                "teknis": {
                    "country_code": parsed_number.country_code,
                    "national_number": parsed_number.national_number,
                    "number_type": phonenumbers.number_type(parsed_number),
                    "area_code": prefix
                }
            }
            
            # Simpna ke database
            self.save_analysis(phone_number, result)
            
            return result

        except Exception as e:
            return {"error": f"Terjadi kesalahan: {str(e)}"}

    def save_analysis(self, phone_number, result):
        conn = sqlite3.connect('phone_analysis.db')
        c = conn.cursor()
        c.execute("""INSERT INTO analysis_history VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (phone_number,
                  datetime.now().isoformat(),
                  result['provider']['nama'],
                  result['lokasi']['region'],
                  result['validasi']['valid'],
                  result['nomor']['kategori'],
                  json.dumps(result)))
        conn.commit()
        conn.close()

    def get_number_type(self, parsed_number):
        number_type = phonenumbers.number_type(parsed_number)
        number_type_dict = {
            0: "FIXED_LINE",
            1: "MOBILE",
            2: "FIXED_LINE_OR_MOBILE",
            3: "TOLL_FREE",
            4: "PREMIUM_RATE",
            5: "SHARED_COST",
            6: "VOIP",
            7: "PERSONAL_NUMBER",
            8: "PAGER",
            9: "UAN",
            10: "UNKNOWN"
        }
        return number_type_dict.get(number_type, "Unknown")

def main():
    analyzer = PhoneNumberAnalyzer()
    
    print("""
▄───▄
█▀█▀█
█▄█▄█
─███──▄▄
─████▐█─█
─████───█
─▀▀▀▀▀▀▀

    Telepon OSINT Tools
""")
    print("Masukkan nomor telepon dengan kode negara")
    print("Contoh: +6281234567890")
    
    while True:
        phone_number = input("\nMasukkan nomor telepon (atau 'q' untuk keluar): ")
        
        if phone_number.lower() == 'q':
            break
            
        result = analyzer.analyze_phone_number(phone_number)
        
        if "error" in result:
            print(f"\nError: {result['error']}")
        else:
            print("\nHasil Analisis Detail:")
            
            print("\n1. Informasi Nomor:")
            print(f"Nomor Original: {result['nomor']['original']}")
            print(f"Format Nasional: {result['nomor']['format_nasional']}")
            print(f"Format Internasional: {result['nomor']['format_internasional']}")
            print(f"Format E164: {result['nomor']['format_e164']}")
            print(f"Kategori: {result['nomor']['kategori']}")
            
            print("\n2. Validasi:")
            print(f"Valid: {'Ya' if result['validasi']['valid'] else 'Tidak'}")
            print(f"Kemungkinan: {'Ya' if result['validasi']['kemungkinan'] else 'Tidak'}")
            print(f"Tipe Nomor: {result['validasi']['tipe_nomor']}")
            
            print("\n3. Provider:")
            print(f"Nama: {result['provider']['nama']}")
            print(f"Network Type: {result['provider']['network_type']}")
            print("\nDetail Provider:")
            for key, value in result['provider']['detail'].items():
                print(f"- {key}: {value}")
            
            print("\n4. Lokasi:")
            print(f"Negara: {result['lokasi']['negara']}")
            print(f"Kode Negara: {result['lokasi']['kode_negara']}")
            print(f"Region: {result['lokasi']['region']}")
            print(f"Zona Waktu: {', '.join(result['lokasi']['zona_waktu'])}")
            print(f"Carrier Region: {result['lokasi']['carrier_region']}")
            
            print("\n5. Informasi Teknis:")
            print(f"Country Code: {result['teknis']['country_code']}")
            print(f"National Number: {result['teknis']['national_number']}")
            print(f"Area Code: {result['teknis']['area_code']}")

if __name__ == "__main__":
    main()