import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import requests
import json
from datetime import datetime
import pytz
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
import folium
import logging
import os
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

class PhoneIntelligence:
    def __init__(self):
        self.setup_logging()
        self.console = Console()
        self.ua = UserAgent()
        
    def setup_logging(self):
        logging.basicConfig(
            filename='phone_osint.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def search_number_reputation(self, number: str) -> Dict[str, Any]:
        results = {
            "spam_score": 0,
            "reports_count": 0,
            "trust_score": 100,
            "last_report": None
        }
        
        apis = {
            "truecaller": f"https://search5-noneu.truecaller.com/v2/search?q={number}",
            "scam": f"https://scam.directory/api/v1/phone/{number}"
        }
        
        headers = {'User-Agent': self.ua.random}
        
        for source, url in apis.items():
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if source == "truecaller" and "score" in data:
                        results["trust_score"] = data["score"]
                    elif source == "scam" and "reports" in data:
                        results["reports_count"] = len(data["reports"])
                        if data["reports"]:
                            results["last_report"] = data["reports"][-1]["date"]
                            results["spam_score"] += 10 * len(data["reports"])
            except:
                continue
                
        return results

    def check_social_media(self, number: str) -> Dict[str, bool]:
        platforms = {
            'telegram': f'https://t.me/{number}',
            'whatsapp': f'https://wa.me/{number}',
            'facebook': f'https://facebook.com/search/top/?q={number}'
        }
        
        results = {}
        headers = {'User-Agent': self.ua.random}
        
        for platform, url in platforms.items():
            try:
                response = requests.head(url, headers=headers, timeout=5)
                results[platform] = response.status_code == 200
            except:
                results[platform] = False
                
        return results

    def get_location_info(self, parsed_number) -> Dict[str, Any]:
        country = geocoder.description_for_number(parsed_number, "id")
        region = geocoder.description_for_number(parsed_number, "en")
        
        location = {
            "country": country,
            "region": region,
            "coordinates": None
        }
        
        try:
            geocoding_url = f"https://nominatim.openstreetmap.org/search?country={country}&format=json"
            response = requests.get(geocoding_url, headers={'User-Agent': self.ua.random})
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                location["coordinates"] = {
                    "latitude": float(data['lat']),
                    "longitude": float(data['lon'])
                }
        except:
            pass
            
        return location

    def generate_report(self, phone_number: str) -> Dict[str, Any]:
        try:
            parsed = phonenumbers.parse(phone_number)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Nomor telepon tidak valid")

            basic_info = {
                "format_internasional": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                "format_nasional": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
                "format_e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
                "kode_negara": f"+{parsed.country_code}",
                "nomor_nasional": parsed.national_number,
                "tipe": str(phonenumbers.number_type(parsed)).split('.')[-1]
            }

            location = self.get_location_info(parsed)

            carrier_info = {
                "provider": carrier.name_for_number(parsed, "id"),
                "tipe_jaringan": basic_info["tipe"]
            }

            tz_list = timezone.time_zones_for_number(parsed)
            timezone_info = {
                "zona_waktu": tz_list[0] if tz_list else "Unknown",
                "waktu_lokal": datetime.now(pytz.timezone(tz_list[0])).strftime("%Y-%m-%d %H:%M:%S") if tz_list else "Unknown"
            }

            reputation = self.search_number_reputation(phone_number)
            social_media = self.check_social_media(phone_number)

            report = {
                "informasi_dasar": basic_info,
                "lokasi": location,
                "operator": carrier_info,
                "zona_waktu": timezone_info,
                "reputasi": reputation,
                "media_sosial": social_media,
                "waktu_analisis": datetime.now().isoformat()
            }

            if location["coordinates"]:
                m = folium.Map(
                    location=[location["coordinates"]["latitude"], location["coordinates"]["longitude"]],
                    zoom_start=10
                )
                folium.Marker(
                    [location["coordinates"]["latitude"], location["coordinates"]["longitude"]],
                    popup=basic_info["format_internasional"]
                ).add_to(m)
                m.save('lokasi_nomor.html')

            return report

        except Exception as e:
            logging.error(f"Error analyzing number {phone_number}: {str(e)}")
            raise

    def display_report(self, report: Dict[str, Any]):
        for section, data in report.items():
            if isinstance(data, dict):
                table = Table(title=section.replace('_', ' ').title())
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                for key, value in data.items():
                    table.add_row(key.replace('_', ' ').title(), str(value))
                self.console.print(table)
                self.console.print("")

def main():
    analyzer = PhoneIntelligence()
    console = Console()
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

    while True:
        try:
            phone = console.input("\n[cyan]Masukkan nomor telepon (+6281234567890) atau 'quit': [/cyan]")
            if phone.lower() == 'quit':
                break

            with console.status("[bold green]Menganalisis nomor..."):
                report = analyzer.generate_report(phone)
                analyzer.display_report(report)
                
                with open(f'report_{phone}.json', 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                console.print(f"\n[green]Report tersimpan di report_{phone}.json[/green]")

        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()