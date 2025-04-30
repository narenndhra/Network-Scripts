import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import sys

def run_nmap(ip, command):
    full_command = f"{command} {ip}"
    result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
    return full_command, result.stdout

def save_output_to_html(ip, command, output, folder):
    filename = os.path.join(folder, f"{ip.replace('.', '_')}.html")
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                background-color: black;
                color: white;
                font-family: monospace;
            }}
            pre {{
                white-space: pre-wrap; /* This makes the text wrap */
                word-wrap: break-word; /* This makes long words break */
                padding: 10px;
            }}
            .command {{
                background-color: #FF0000; /* Red background */
                color: white;
                padding: 5px;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <pre><span class="command"><strong>Command:</strong> {command}</span><br><br>{output}</pre>
    </body>
    </html>
    """
    with open(filename, "w") as file:
        file.write(html_content)
    return filename

def generate_screenshot(html_file):
    image_file = html_file.replace(".html", ".png")
    command = f"wkhtmltoimage {html_file} {image_file}"
    subprocess.run(command, shell=True)
    return image_file

def process_ip(ip, command, folder, progress_data):
    try:
        full_command, output = run_nmap(ip, command)
        html_file = save_output_to_html(ip, full_command, output, folder)
        generate_screenshot(html_file)
        os.remove(html_file)  # Optional: Delete the HTML file if you only need the screenshots
        progress_data[ip] = "Success"
    except Exception as e:
        progress_data[ip] = f"Error: {e}"

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <nmap_command> <ip_list_file>")
        sys.exit(1)

    nmap_command = sys.argv[1]
    ip_list_file = sys.argv[2]

    with open(ip_list_file, "r") as file:
        ips = [line.strip() for line in file]

    folder = "http_nse"
    if not os.path.exists(folder):
        os.makedirs(folder)

    total_ips = len(ips)
    progress_data = {}

    start_time = time.time()

    # Overall progress bar
    with tqdm(total=total_ips, desc="Overall Progress", unit="IP") as overall_pbar:
        # Use ThreadPoolExecutor to manage concurrent tasks
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_ip, ip, nmap_command, folder, progress_data): ip for ip in ips}

            # Update progress bar as tasks complete
            for future in as_completed(futures):
                ip = futures[future]
                overall_pbar.set_postfix_str(f"Current IP: {ip}")
                overall_pbar.update(1)
                try:
                    future.result()  # This will also propagate any exceptions raised
                except Exception as e:
                    progress_data[ip] = f"Exception: {e}"

    end_time = time.time()
    elapsed_time = end_time - start_time

    # Count successful screenshots
    screenshot_count = sum(1 for status in progress_data.values() if status == "Success")
    failed_ips = [ip for ip, status in progress_data.items() if status != "Success"]

    # Report results
    print("\nSummary Report:")
    print(f"Total IPs in text file: {total_ips}")
    print(f"Screenshots taken: {screenshot_count}")
    print(f"Time taken for overall process: {elapsed_time:.2f} seconds")

    if failed_ips:
        missing_count = len(failed_ips)
        print(f"Missing screenshots: {missing_count}")
        print("IPs with missing screenshots:")
        for ip in failed_ips:
            print(f"IP: {ip} - Status: {progress_data[ip]}")

if __name__ == "__main__":
    main()
