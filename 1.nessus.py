import pandas as pd
import os
import subprocess
import time
import concurrent.futures
from tqdm import tqdm

# Function to parse the CSV file and extract vulnerabilities by severity for each IP
def parse_nessus_csv(csv_file):
    df = pd.read_csv(csv_file)
    ips_vulns = {}

    for _, row in df.iterrows():
        ip = row['Host'].strip()
        severity = row['Risk'].strip().lower() if pd.notna(row['Risk']) else 'info'
        title = row['Name'].strip()
        os_info = row.get('Operating System', 'Unknown').strip()  # Handle missing 'Operating System' column
        
        if ip not in ips_vulns:
            ips_vulns[ip] = {'critical': [], 'high': [], 'medium': [], 'low': [], 'info': [], 'os_info': os_info}
        
        if severity in ['critical', 'high', 'medium', 'low', 'info']:
            ips_vulns[ip][severity].append(title)
    
    return ips_vulns

# Function to create a simple HTML summary of the vulnerabilities with detailed information
def create_html_summary(ip, vulnerabilities, scan_start_time, scan_end_time):
    color_map = {
        'critical': '#c9302c',
        'high': '#d9534f',
        'medium': '#f0ad4e',
        'low': '#5bc0de',
        'info': '#5bc0de'
    }

    severity_counts = {severity: len(vulns) for severity, vulns in vulnerabilities.items() if severity != 'os_info'}
    os_info = vulnerabilities['os_info']

    html_content = f"""
    <html>
    <head><style>
    body {{ font-family: 'Arial', sans-serif; background-color: white; color: black; margin: 20px; }}
    h1 {{ color: black; text-align: center; font-size: 2em; margin-bottom: 0.5em; }}
    h2 {{ font-size: 1.5em; color: black; margin-top: 30px; }}
    table {{ width: 100%; margin: 20px auto; border-collapse: collapse; }}
    th, td {{ padding: 15px; text-align: center; border: 1px solid #ddd; }}
    th {{ background-color: #f2f2f2; font-size: 1.2em; }}
    .severity-title {{
        font-size: 1.5em;
        margin: 10px 0;
        padding: 10px;
        color: white;
        text-align: center;
        border-radius: 5px;
    }}
    .critical {{ background-color: {color_map['critical']}; }}
    .high {{ background-color: {color_map['high']}; }}
    .medium {{ background-color: {color_map['medium']}; }}
    .low {{ background-color: {color_map['low']}; }}
    .info {{ background-color: {color_map['info']}; }}
    .vuln-list {{
        margin-left: 20px;
        font-size: 1.1em;
        list-style-type: disc;
    }}
    .vuln-list li {{
        margin-bottom: 5px;
    }}
    </style></head>
    <body>
    <h1>Vulnerability Report for {ip}</h1>
    
    <h2>Scan Information</h2>
    <table>
        <tr>
            <th>Start Time</th>
            <th>End Time</th>
        </tr>
        <tr>
            <td>{scan_start_time}</td>
            <td>{scan_end_time}</td>
        </tr>
    </table>
    
    <h2>Host Information</h2>
    <table>
        <tr>
            <th>IP Address</th>
            <th>Operating System</th>
        </tr>
        <tr>
            <td>{ip}</td>
            <td>{os_info}</td>
        </tr>
    </table>

    <h2>Vulnerability Summary</h2>
    <table>
        <tr>
            <th>Critical</th>
            <th>High</th>
            <th>Medium</th>
            <th>Low</th>
            <th>Info</th>
        </tr>
        <tr>
            <td style="background-color: {color_map['critical']};">{severity_counts['critical']}</td>
            <td style="background-color: {color_map['high']};">{severity_counts['high']}</td>
            <td style="background-color: {color_map['medium']};">{severity_counts['medium']}</td>
            <td style="background-color: {color_map['low']};">{severity_counts['low']}</td>
            <td style="background-color: {color_map['info']};">{severity_counts['info']}</td>
        </tr>
    </table>
    """

    for severity, vulns in vulnerabilities.items():
        if severity in color_map and vulns:
            html_content += f'<div class="severity-title {severity}">{severity.capitalize()} Vulnerabilities:</div>'
            html_content += '<ul class="vuln-list">'
            for vuln in vulns[:5]:  # Show first few items
                html_content += f'<li>{vuln}</li>'
            html_content += '</ul>'
    
    html_content += "<br/><br/></body></html>"  # Adding extra space at the bottom
    
    return html_content

# Function to save the HTML to a file
def save_html_to_file(html_content, file_name):
    with open(file_name, 'w') as file:
        file.write(html_content)

# Function to capture screenshot using wkhtmltoimage
def capture_screenshot(html_file, screenshot_file):
    # We remove the --width and --height flags so that the content is captured fully without being cut off.
    command = ['wkhtmltoimage', '--disable-smart-width', html_file, screenshot_file]
    subprocess.run(command)

# Function to process each IP and generate HTML and screenshot
def process_ip(ip, vulnerabilities, output_folder, scan_start_time, scan_end_time):
    html_summary = create_html_summary(ip, vulnerabilities, scan_start_time, scan_end_time)
    html_file = os.path.join(output_folder, f"{ip}.html")
    screenshot_file = os.path.join(output_folder, f"{ip}.png")
    
    save_html_to_file(html_summary, html_file)
    capture_screenshot(html_file, screenshot_file)
    
    os.remove(html_file)
    return ip

# Main script logic
def main(folder_path):
    start_time = time.time()
    scan_start_time = "Thu Aug 8 10:03:41 2024"  # Example, replace with actual
    scan_end_time = "Thu Aug 8 10:12:15 2024"    # Example, replace with actual

    for csv_file in os.listdir(folder_path):
        if csv_file.endswith('.csv'):
            csv_file_path = os.path.join(folder_path, csv_file)
            csv_name = os.path.splitext(csv_file)[0]
            output_folder = os.path.join('nessus_screenshots', csv_name)

            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            ips_vulns = parse_nessus_csv(csv_file_path)
            total_ips = len(ips_vulns)

            with tqdm(total=total_ips, desc=f"Processing {csv_file}", ncols=100, bar_format="{{l_bar}}{{bar}}| {{n_fmt}}/{{total_fmt}} IPs Processed") as pbar:
                with concurrent.futures.ProcessPoolExecutor() as executor:
                    futures = {
                        executor.submit(process_ip, ip, vulnerabilities, output_folder, scan_start_time, scan_end_time): ip
                        for ip, vulnerabilities in ips_vulns.items()
                    }
                    for future in concurrent.futures.as_completed(futures):
                        pbar.update(1)

    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Screenshots saved in 'nessus_screenshots' folder")

if __name__ == "__main__":
    folder_path = input("Enter the path to the folder containing Nessus CSV reports: ")
    main(folder_path)
