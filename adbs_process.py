#This script combines the ADS-B decodinf script and CLI script to aquire and process ADS-B data
import pyModeS as pms
import time
from collections import defaultdict
import subprocess

#python command to run dump1090 and pipe the output to the script
cmd = ['dump1090', '--raw']
result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1)


position_count = 0
total_count = 0

# Matrix structure: dictionary indexed by ICAO, each entry contains:
# [0] icao, [1] odd_msg, [2] even_msg, [3] odd_time, [4] even_time
aircraft_matrix = {}

# Position matrix structure: dictionary indexed by ICAO, each entry contains:
# [0] icao, [1] lat, [2] long, [3] altitude
position_matrix = {}

def visualize_matrix(aircraft_matrix):
    """Print the matrix structure showing all columns and rows"""
    if not aircraft_matrix:
        print("\nMatrix is empty\n")
        return
    
    print("\n" + "="*100)
    print("MATRIX STATE")
    print("="*100)
    
    # Get all ICAOs (columns)
    icaos = list(aircraft_matrix.keys())
    
    # Calculate column widths
    col_width = 25
    row_names = ["ICAO", "odd_msg", "even_msg", "odd_time", "even_time", "altitude", "time_since_last_message"]
    
    # Print ICAO row first
    icao_row_str = "ICAO".ljust(12)
    for icao in icaos:
        icao_row_str += str(icao).ljust(col_width)
    print(icao_row_str)
    print("-" * len(icao_row_str))
    
    # Print remaining rows (skip ICAO since we already printed it)
    for row_idx, row_name in enumerate(row_names[1:], 1):
        row_str = row_name.ljust(12)
        for icao in icaos:
            data = aircraft_matrix[icao]
            if row_name == "ICAO":
                value = str(data['icao']) if data['icao'] else "None"
            elif row_name == "odd_msg":
                value = "YES" if data['odd_msg'] else "None"
            elif row_name == "even_msg":
                value = "YES" if data['even_msg'] else "None"
            elif row_name == "odd_time":
                value = f"{data['odd_time']:.2f}" if data['odd_time'] else "None"
            elif row_name == "even_time":
                value = f"{data['even_time']:.2f}" if data['even_time'] else "None"
            elif row_name == "altitude":
                value = str(data['altitude']) if data['altitude'] else "None"
            elif row_name == "time_since_last_message":
                value = f"{data['last_message_time']:.2f}" if data['last_message_time'] else "None"
            row_str += str(value).ljust(col_width)
        print(row_str)
    
    print("="*100 + "\n")

def visualize_position_matrix(position_matrix):
    """Print the position matrix structure showing all columns and rows"""
    if not position_matrix:
        print("\nPosition Matrix is empty\n")
        return
    
    print("\n" + "="*100)
    print("POSITION MATRIX STATE")
    print("="*100)
    
    # Get all ICAOs (columns)
    icaos = list(position_matrix.keys())
    
    # Calculate column widths
    col_width = 25
    row_names = ["ICAO", "lat", "long", "altitude"]
    
    # Print ICAO row first
    icao_row_str = "ICAO".ljust(12)
    for icao in icaos:
        icao_row_str += str(icao).ljust(col_width)
    print(icao_row_str)
    print("-" * len(icao_row_str))
    
    # Print remaining rows (skip ICAO since we already printed it)
    for row_idx, row_name in enumerate(row_names[1:], 1):
        row_str = row_name.ljust(12)
        for icao in icaos:
            data = position_matrix[icao]
            if row_name == "ICAO":
                value = str(data['icao']) if data['icao'] else "None"
            elif row_name == "lat":
                value = f"{data['lat']:.6f}" if data['lat'] is not None else "None"
            elif row_name == "long":
                value = f"{data['long']:.6f}" if data['long'] is not None else "None"
            elif row_name == "altitude":
                value = str(data['altitude']) if data['altitude'] is not None else "None"
            row_str += str(value).ljust(col_width)
        print(row_str)
    
    print("="*100 + "\n")

def handle_dump1090():
    global aircraft_matrix, position_matrix
    global position_count, total_count

    try:
        for line in result.stdout:
            line = line.decode("ascii", errors="ignores").strip()
            current_time = time.time()
            total_count += 1
            # # Remove the "*" at the start and the ";" at the end
            cleaned = line.lstrip('*').rstrip(';\n')

            tc = pms.decoder.adsb.typecode(cleaned)
            #check if the message is a position message
            if 5 <= tc <= 18:
                position_count += 1
                #get the icao address of the aircraft
                icao = pms.decoder.adsb.icao(cleaned)
                altitude = pms.decoder.adsb.altitude(cleaned)
                
                # Initialize new column if ICAO doesn't exist
                if icao not in aircraft_matrix:
                    aircraft_matrix[icao] = {
                        'icao': icao,
                        'altitude': altitude,
                        'odd_msg': None,
                        'even_msg': None,
                        'odd_time': None,
                        'even_time': None,
                        'last_message_time': None
                    }
                
                # Initialize new column in position matrix if ICAO doesn't exist
                if icao not in position_matrix:
                    position_matrix[icao] = {
                        'icao': icao,
                        'lat': None,
                        'long': None,
                        'altitude': None
                    }
                
                # Update the appropriate row based on oe_flag
                if pms.decoder.adsb.oe_flag(cleaned) == 1:
                    # Odd message - update row 1 (odd_msg) and row 3 (odd_time)
                    aircraft_matrix[icao]['odd_msg'] = cleaned
                    aircraft_matrix[icao]['odd_time'] = current_time
                    aircraft_matrix[icao]['last_message_time'] = current_time
                else:
                    # Even message - update row 2 (even_msg) and row 4 (even_time)
                    aircraft_matrix[icao]['even_msg'] = cleaned
                    aircraft_matrix[icao]['even_time'] = current_time
                    aircraft_matrix[icao]['last_message_time'] = current_time
                
                # Visualize the matrices after each update
                visualize_matrix(aircraft_matrix)
                #time.sleep(3)
                
                # After updating the matrix, check ALL columns and calculate positions for every populated column
                for icao_key, aircraft_data in aircraft_matrix.items():
                    odd_msg = aircraft_data['odd_msg']
                    even_msg = aircraft_data['even_msg']
                    odd_time = aircraft_data['odd_time']
                    even_time = aircraft_data['even_time']
                    
                    # Check if all 5 rows are populated (icao, odd_msg, even_msg, odd_time, even_time)
                    all_populated = (aircraft_data['icao'] is not None and 
                                   odd_msg is not None and 
                                   even_msg is not None and 
                                   odd_time is not None and 
                                   even_time is not None)
                    
                    # Calculate position for every column that has all 5 rows populated
                    if all_populated:

                        try:
                            #attempt to calculate the position of the aircraft
                            position = pms.decoder.adsb.position(even_msg, odd_msg, even_time, odd_time)
                            lat, lon = position
                            
                            # Update position matrix with calculated values
                            if icao_key in position_matrix:
                                position_matrix[icao_key]['lat'] = lat
                                position_matrix[icao_key]['long'] = lon
                                position_matrix[icao_key]['altitude'] = aircraft_data.get('altitude')
                            
                        except Exception as e:
                            print("Error calculating position for " + icao_key + ": " + str(e))
                            print("\n")

                visualize_position_matrix(position_matrix)

                print("position messages received: " + str(position_count))
                print("total messages received: " + str(total_count))
                time.sleep(0.1)

            # if the message is not a position message, continue
            else:
                #time.sleep(0.5)
                continue
    except KeyboardInterrupt:
        pass

handle_dump1090()