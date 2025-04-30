import os
import pandas as pd
import textwrap
import imgkit
from multiprocessing import Pool

# Function to create screenshots with HTML and CSS
def create_screenshot(ip, vuln_name, protocol, port, plugin_output, output_dir):
    # Create directory for the IP if it doesn't exist
    ip_dir = os.path.join(output_dir, ip)
    os.makedirs(ip_dir, exist_ok=True)

    # Truncate the vulnerability name if too long
    vuln_filename = vuln_name[:50] + '...' if len(vuln_name) > 50 else vuln_name
    vuln_filename = vuln_filename.replace(" ", "_").replace("/", "_")

    # Wrap the plugin output text
    wrapped_output = "<br>".join(textwrap.wrap(plugin_output, width=95))

    # HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f0f0f0;
                margin: 0;
                padding: 20px;
                color: #000;
            }}
            h3 {{
                color: #3c3c3c;
            }}
            .code-block {{
                background-color: #e6e6e6;
                padding: 15px;
                border: 1px solid #b4b4b4;
                font-family: Courier, monospace;
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <h3><b>Plugin Output</b></h3>
        <hr>
        <p><b>{protocol}/{port}</b></p>
        <div class="code-block">{wrapped_output}</div>
    </body>
    </html>
    """

    # Options to disable external resource loading
    options = {
        'no-images': '',
        'disable-local-file-access': ''
    }

    # Convert HTML to PNG using imgkit
    screenshot_path = os.path.join(ip_dir, f'{vuln_filename}.png')
    imgkit.from_string(html_content, screenshot_path, options=options)

# Function to process each IP and its associated vulnerabilities
def process_ip(ip, vulnerabilities, output_dir):
    for index, row in vulnerabilities.iterrows():
        vuln_name = row['Name']
        protocol = row['Protocol']
        port = row['Port']
        plugin_output = row['Plugin Output']
        
        # Handle possible NaN values in plugin_output
        if pd.isna(plugin_output):
            plugin_output = ""
        
        create_screenshot(ip, vuln_name, protocol, port, plugin_output, output_dir)

def main():
    # Load the CSV file
    input_csv = input("Enter the path to the CSV file: ")
    df = pd.read_csv(input_csv)

    # Use the correct column names based on your CSV file
    ip_column = 'Host'
    plugin_output_column = 'Plugin Output'
    plugin_name_column = 'Name'
    protocol_column = 'Protocol'
    port_column = 'Port'

    # Pre-process and extract necessary columns
    ip_addresses = df[ip_column].unique()
    vulnerabilities = df[[ip_column, plugin_name_column, plugin_output_column, protocol_column, port_column]]

    # Directory to save the screenshots
    output_dir = './screenshots'
    os.makedirs(output_dir, exist_ok=True)

    # Use multiprocessing to process each IP in parallel
    ip_process_info = [(ip, vulnerabilities[vulnerabilities[ip_column] == ip], output_dir) for ip in ip_addresses]

    with Pool(processes=3) as pool:  # Adjust the number of processes if needed
        pool.starmap(process_ip, ip_process_info)

    print("Screenshots created successfully.")

if __name__ == "__main__":
    main()
