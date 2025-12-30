import pyModeS as pms
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from collections import defaultdict
import threading
import queue

class ADSBTracker:
    def __init__(self):
        self.aircraft_data = defaultdict(dict)
        self.data_queue = queue.Queue()
        self.console = Console()
        
    def parse_hex_data(self, hex_string):
        """Parse hex data and extract aircraft information"""
        try:
            # Clean the hex string
            cleaned = hex_string.lstrip('*').rstrip(';\n')
            
            # Get basic info
            df = pms.df(cleaned)
            icao = pms.icao(cleaned)
            
            if not icao:
                return None
                
            aircraft_info = {
                'icao': icao,
                'df': df,
                'speed': 'N/A',
                'cpr_lat': 'N/A',
                'cpr_long': 'N/A',
                'altitude': 'N/A',
                'last_update': time.time()
            }
            
            # Parse different message types
            if df == 17:  # ADS-B message
                tc = pms.adsb.typecode(cleaned)
                
                if tc >= 9 and tc <= 18:  # Airborne position
                    try:
                        alt = pms.adsb.altitude(cleaned)
                        if alt:
                            aircraft_info['altitude'] = f"{alt} ft"
                    except:
                        pass
                        
                    try:
                        lat, lon = pms.adsb.position(cleaned)
                        if lat and lon:
                            aircraft_info['cpr_lat'] = f"{lat:.6f}"
                            aircraft_info['cpr_long'] = f"{lon:.6f}"
                    except:
                        pass
                        
                elif tc == 19:  # Airborne velocity
                    try:
                        spd = pms.adsb.speed(cleaned)
                        if spd:
                            aircraft_info['speed'] = f"{spd} kts"
                    except:
                        pass
                        
            elif df == 4:  # Surveillance altitude reply
                try:
                    alt = pms.commb.altitude(cleaned)
                    if alt:
                        aircraft_info['altitude'] = f"{alt} ft"
                except:
                    pass
                    
            elif df == 20:  # Surveillance altitude reply
                try:
                    alt = pms.commb.altitude(cleaned)
                    if alt:
                        aircraft_info['altitude'] = f"{alt} ft"
                except:
                    pass
            
            return aircraft_info
            
        except Exception as e:
            return None
    
    def process_file(self, filename):
        """Process hexstream file and add data to queue"""
        try:
            with open(filename, 'r') as file:
                for line in file:
                    aircraft_info = self.parse_hex_data(line)
                    if aircraft_info:
                        self.data_queue.put(aircraft_info)
                    time.sleep(0.1)  # Small delay to make it readable
        except FileNotFoundError:
            self.console.print(f"[red]The file {filename} does not exist.[/red]")
        except Exception as e:
            self.console.print(f"[red]An error occurred: {e}[/red]")
    
    def update_aircraft_data(self):
        """Update aircraft data from queue"""
        while not self.data_queue.empty():
            try:
                aircraft_info = self.data_queue.get_nowait()
                icao = aircraft_info['icao']
                self.aircraft_data[icao].update(aircraft_info)
            except queue.Empty:
                break
    
    def create_table(self):
        """Create the display table"""
        table = Table(title="ADS-B Aircraft Tracker", show_header=True, header_style="bold magenta")
        
        table.add_column("ICAO Address", style="cyan", width=12)
        table.add_column("DF", style="green", width=4)
        table.add_column("Speed", style="yellow", width=10)
        table.add_column("CPR Latitude", style="blue", width=12)
        table.add_column("CPR Longitude", style="blue", width=12)
        table.add_column("Altitude", style="red", width=10)
        table.add_column("Last Update", style="dim", width=8)
        
        # Add aircraft data to table
        for icao, data in self.aircraft_data.items():
            last_update = int(time.time() - data.get('last_update', 0))
            table.add_row(
                data.get('icao', 'N/A'),
                str(data.get('df', 'N/A')),
                data.get('speed', 'N/A'),
                data.get('cpr_lat', 'N/A'),
                data.get('cpr_long', 'N/A'),
                data.get('altitude', 'N/A'),
                f"{last_update}s ago"
            )
        
        return table
    
    def run_tui(self, filename):
        """Run the TUI"""
        # Start file processing in a separate thread
        file_thread = threading.Thread(target=self.process_file, args=(filename,), daemon=True)
        file_thread.start()
        
        # Main TUI loop
        with Live(self.create_table(), refresh_per_second=2, console=self.console) as live:
            try:
                while True:
                    self.update_aircraft_data()
                    live.update(self.create_table())
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Exiting ADS-B Tracker...[/yellow]")

if __name__ == "__main__":
    tracker = ADSBTracker()
    tracker.run_tui("hexstream.txt")
