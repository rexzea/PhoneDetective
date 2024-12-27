import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import requests
import json
from datetime import datetime
import pytz
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
import folium
import logging
import os
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import re
import shodan
import socket
import whois
import dns.resolver
import ipwhois
from email_validator import validate_email
from urllib.parse import urlparse
import pandas as pd

class PhoneIntelligence:
    def __init__(self):
        self.setup_logging()
        self.console = Console()
        self.ua = UserAgent()
        self.setup_apis()
        
    def setup_logging(self):
        logging.basicConfig(
            filename='phone_osint.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def setup_apis(self):
        self.apis = {
            'shodan': os.getenv('SHODAN_API_KEY'),
            'virustotal': os.getenv('VT_API_KEY'),
            'numverify': os.getenv('NUMVERIFY_API_KEY'),
            'hibp': os.getenv('HIBP_API_KEY')
        }

    def get_deep_carrier_info(self, number: str, parsed) -> Dict[str, Any]:
        carrier_info = {
            "name": carrier.name_for_number(parsed, "id"),
            "type": str(phonenumbers.number_type(parsed)).split('.')[-1],
            "network_type": "Unknown",
            "portability": "Unknown",
            "coverage_details": {},
            "technology": []
        }
        
        try:
            mcc = str(parsed.country_code)
            mnc = str(parsed.national_number)[:3]

            carrier_db_url = f"https://mcc-mnc-list.com/list/{mcc}-{mnc}"
            response = requests.get(carrier_db_url, headers={'User-Agent': self.ua.random})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                carrier_info.update(self._parse_carrier_details(soup))

            port_check_url = f"https://numverify.com/portability/{number}"
            response = requests.get(port_check_url, headers={'User-Agent': self.ua.random})
            if response.status_code == 200:
                carrier_info["portability"] = "Ported" if "ported" in response.text.lower() else "Original"
                
        except Exception as e:
            logging.error(f"Error getting carrier info: {str(e)}")
            
        return carrier_info

    def get_location_details(self, parsed_number) -> Dict[str, Any]:
        country = geocoder.description_for_number(parsed_number, "id")
        region = geocoder.description_for_number(parsed_number, "en")
        
        location = {
            "country": country,
            "region": region,
            "city": "Unknown",
            "coordinates": None,
            "timezone_details": {},
            "area_details": {},
            "demographics": {},
            "isp_coverage": []
        }
        
        try:
            geocoding_url = f"https://nominatim.openstreetmap.org/search?country={country}&format=json"
            response = requests.get(geocoding_url, headers={'User-Agent': self.ua.random})
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                location.update(self._parse_location_data(data))
                
            if location["coordinates"]:
                self._enrich_location_data(location)
                
        except Exception as e:
            logging.error(f"Error getting location details: {str(e)}")
            
        return location

    def check_number_security(self, number: str) -> Dict[str, Any]:
        security_info = {
            "risk_score": 0,
            "spam_reports": [],
            "dark_web_mentions": 0,
            "breach_associations": [],
            "malicious_activities": [],
            "voip_detection": False,
            "recent_scam_patterns": [],
            "security_recommendations": []
        }
        
        try:
            security_info.update(self._check_security_databases(number))

            security_info.update(self._check_dark_web(number))

            security_info.update(self._analyze_scam_patterns(number))
            
            security_info["risk_score"] = self._calculate_risk_score(security_info)
            
            security_info["security_recommendations"] = self._generate_security_recommendations(security_info)
            
        except Exception as e:
            logging.error(f"Error checking security: {str(e)}")
            
        return security_info

    def analyze_digital_footprint(self, number: str) -> Dict[str, Any]:
        footprint = {
            "social_media": {},
            "messaging_apps": {},
            "online_services": {},
            "public_records": [],
            "websites_mentioned": [],
            "apps_associated": [],
            "last_seen_online": None,
            "activity_score": 0
        }
        
        try:
            platforms = [
                'facebook', 'instagram', 'twitter', 'linkedin', 'telegram',
                'whatsapp', 'viber', 'signal', 'line', 'wechat'
            ]
            
            for platform in platforms:
                result = self._check_platform(number, platform)
                if result:
                    footprint["social_media"][platform] = result
            
            messaging_apps = ['telegram', 'whatsapp', 'viber', 'signal']
            for app in messaging_apps:
                status = self._check_messaging_app(number, app)
                footprint["messaging_apps"][app] = status
            
            footprint["websites_mentioned"] = self._search_web_mentions(number)
            
            footprint["activity_score"] = self._calculate_activity_score(footprint)
            
        except Exception as e:
            logging.error(f"Error analyzing digital footprint: {str(e)}")
            
        return footprint

    def get_network_details(self, parsed_number) -> Dict[str, Any]:
        network_info = {
            "carrier": carrier.name_for_number(parsed_number, "id"),
            "network_type": "Unknown",
            "infrastructure": {},
            "capabilities": [],
            "coverage": {},
            "known_issues": []
        }
        
        try:
            carrier_name = network_info["carrier"]
            if carrier_name:
                network_info.update(self._get_carrier_infrastructure(carrier_name))
            
            network_info["capabilities"] = self._check_network_capabilities(parsed_number)
            
            network_info["coverage"] = self._get_coverage_info(parsed_number)
            
        except Exception as e:
            logging.error(f"Error getting network details: {str(e)}")
            
        return network_info

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
                "tipe": str(phonenumbers.number_type(parsed)).split('.')[-1],
                "valid": phonenumbers.is_valid_number(parsed),
                "kemungkinan": phonenumbers.is_possible_number(parsed)
            }

            report = {
                "informasi_dasar": basic_info,
                "lokasi": self.get_location_details(parsed),
                "operator": self.get_deep_carrier_info(phone_number, parsed),
                "keamanan": self.check_number_security(phone_number),
                "jejak_digital": self.analyze_digital_footprint(phone_number),
                "jaringan": self.get_network_details(parsed),
                "waktu_analisis": datetime.now().isoformat()
            }

            self._generate_visualizations(report)

            return report

        except Exception as e:
            logging.error(f"Error generating report: {str(e)}")
            raise

    def _check_security_databases(self, number: str) -> Dict[str, Any]:
        security_data = {
            "spam_reports": [],
            "blacklist_status": [],
            "reputation_score": 0
        }

        return security_data

    def _check_dark_web(self, number: str) -> Dict[str, Any]:
        return {"dark_web_mentions": 0}

    def _analyze_scam_patterns(self, number: str) -> Dict[str, Any]:
        return {"scam_patterns": []}

    def _calculate_risk_score(self, security_info: Dict[str, Any]) -> int:
        score = 0
        return score

    def _generate_security_recommendations(self, security_info: Dict[str, Any]) -> List[str]:
        recommendations = []
        return recommendations

    def _check_platform(self, number: str, platform: str) -> Dict[str, Any]:
        result = {}
        return result

    def _check_messaging_app(self, number: str, app: str) -> Dict[str, Any]:
        result = {}
        return result

    def _search_web_mentions(self, number: str) -> List[str]:
        mentions = []
        return mentions

    def _calculate_activity_score(self, footprint: Dict[str, Any]) -> int:
        score = 0
        return score

    def _get_carrier_infrastructure(self, carrier_name: str) -> Dict[str, Any]:
        infrastructure = {}
        return infrastructure

    def _check_network_capabilities(self, parsed_number) -> List[str]:
        capabilities = []
        return capabilities

    def _get_coverage_info(self, parsed_number) -> Dict[str, Any]:
        coverage = {}
        return coverage

    def _generate_visualizations(self, report: Dict[str, Any]):
        try:
            if report["lokasi"]["coordinates"]:
                m = folium.Map(
                    location=[
                        report["lokasi"]["coordinates"]["latitude"],
                        report["lokasi"]["coordinates"]["longitude"]
                    ],
                    zoom_start=10
                )
                folium.Marker(
                    [
                        report["lokasi"]["coordinates"]["latitude"],
                        report["lokasi"]["coordinates"]["longitude"]
                    ],
                    popup=report["informasi_dasar"]["format_internasional"]
                ).add_to(m)
                m.save('lokasi_nomor.html')

            
        except Exception as e:
            logging.error(f"Error generating visualizations: {str(e)}")

    def display_report(self, report: Dict[str, Any]):
        for section, data in report.items():
            if isinstance(data, dict):
                table = Table(title=section.replace('_', ' ').title())
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2, ensure_ascii=False)
                    table.add_row(key.replace('_', ' ').title(), str(value))
                
                self.console.print(table)
                self.console.print("")

def main():
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
    analyzer = PhoneIntelligence()
    console = Console()

    while True:
        try:
            phone = console.input("\n[cyan]Masukkan nomor telepon (+6281234567890) atau 'quit': [/cyan]")
            if phone.lower() == 'quit':
                break

            with console.status("[bold green]Menganalisis nomor..."):
                report = analyzer.generate_report(phone)
                analyzer.display_report(report)
                
                # menyimpan laporan
                with open(f'report_{phone}.json', 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                console.print(f"\n[green]Report tersimpan di report_{phone}.json[/green]")
                
                if os.path.exists('lokasi_nomor.html'):
                    console.print("[green]Peta lokasi tersimpan di lokasi_nomor.html[/green]")

        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()