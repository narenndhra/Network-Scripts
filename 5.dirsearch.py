import subprocess
import os
import json
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import shutil
import gc

# Define memory limit (e.g., 75% of total system memory)
MEMORY_LIMIT = 0.75 * psutil.virtual_memory().total

def run_dirsearch(ip):
    output_file = f"{ip.replace('.', '_')}.json"
    command = f"dirsearch -u https://{ip}/ -x 204,400,401,403,404,500,502 -t 50 --format json -o {output_file}"

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        result.check_returncode()
        # Verify if the output file was created
        if not os.path.exists(output_file):
            raise FileNotFoundError(f"Expected output file not found: {output_file}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"dirsearch command failed: {e.stderr}")

    return command, result.stdout, output_file


def filter_and_limit_results(json_data, max_per_group=5):
    seen_urls = set()
    grouped_results = {}

    for result in json_data['results']:
        if result['status'] == 200:
            key = (result['status'], result['content-length'])
            if key not in grouped_results:
                grouped_results[key] = []
            grouped_results[key].append(result)

    content_lengths = {group[0]['content-length'] for group in grouped_results.values()}

    if len(content_lengths) == 1:
        filtered_results = []
        for group in grouped_results.values():
            filtered_results.extend(group[:max_per_group])
    else:
        filtered_results = []
        for group in grouped_results.values():
            filtered_results.extend(group)

    return filtered_results


def format_json_output(filtered_results, json_data, command):
    formatted_output = []
    formatted_output.append(f"_|. _ _  _  _  _ _|_    v0.4.3\n (_||| _) (/_(_|| (_| )\n")
    formatted_output.append(f"Extensions: php, aspx, jsp, html, js | HTTP method: GET | Threads: 50 | Wordlist size: 11460\n")

    formatted_output.append(f"Output File: {json_data['info']['args'].split('--format json -o ')[-1]}\n")
    formatted_output.append(f"Target: {json_data['info']['args'].split('-u ')[1].split(' ')[0]}\n")
    formatted_output.append(f"[{json_data['info']['time']}] Starting:\n")

    for result in filtered_results:
        line = f"[{time.strftime('%H:%M:%S')}] <span class='status'>{result['status']}</span> - <span class='size'>{result['content-length']}B</span>  - <span class='url'>{result['url']}</span>"
        formatted_output.append(line)

    formatted_output.append("\nTask Completed.")
    return "<br>".join(formatted_output)


def save_output_to_html(ip, formatted_output, command, folder):
    filename = os.path.join(folder, f"{ip.replace('.', '_')}.html")
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                background-color: black;
                color: white;
                font-family: monospace;
                margin: 0;
                padding: 20px;
            }}
            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                margin: 0;
                padding: 0;
            }}
            .command {{
                background-color: #FF0000;
                color: white;
                padding: 10px;
                border: 2px solid #FF0000;
                border-radius: 5px;
                display: block;
                overflow: hidden;
                word-break: break-all;
            }}
            .header {{
                color: #00FF00;
                font-weight: bold;
            }}
            .result-row {{
                display: flex;
                justify-content: space-between;
                border-bottom: 1px solid #444;
                padding: 5px 0;
            }}
            .result-row:nth-child(even) {{
                background-color: #222;
            }}
            .result-row span {{
                width: 33%;
                text-align: left;
            }}
            .status {{
                color: #FFD700;
                font-weight: bold;
            }}
            .size {{
                color: #00CCFF;
            }}
            .url {{
                color: #FF99CC;
            }}
        </style>
    </head>
    <body>
        <pre><span class="command"><strong>Command:</strong> {command}</span><br><br>{formatted_output}</pre>
    </body>
    </html>
    """
    with open(filename, "w") as file:
        file.write(html_content)
    return filename


def generate_screenshot(html_file):
    image_file = html_file.replace(".html", ".png")
    command = f"wkhtmltoimage {html_file} {image_file}"

    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Screenshot generation failed: {e.stderr}")

    return image_file


def cleanup_files(ip, output_file, html_file):
    if os.path.exists(output_file):
        os.remove(output_file)
    if os.path.exists(html_file):
        os.remove(html_file)
    gc.collect()


def memory_within_limit():
    current_memory_usage = psutil.virtual_memory().used
    return current_memory_usage < MEMORY_LIMIT


def process_ip(ip, folder, progress_data):
    try:
        command, output, output_file = run_dirsearch(ip)

        with open(output_file, "r") as json_file:
            json_data = json.load(json_file)

        filtered_results = filter_and_limit_results(json_data, max_per_group=5)

        if not filtered_results:
            progress_data[ip] = "No valid 200 OK responses"
            return

        formatted_output = format_json_output(filtered_results, json_data, command)
        html_file = save_output_to_html(ip, formatted_output, command, folder)
        generate_screenshot(html_file)
        cleanup_files(ip, output_file, html_file)

        progress_data[ip] = "Success"
    except Exception as e:
        progress_data[ip] = f"Error: {e}"


def main():
    with open("ip.txt", "r") as file:
        ips = [line.strip() for line in file]

    folder = "dirsearch_results"
    if not os.path.exists(folder):
        os.makedirs(folder)

    total_ips = len(ips)
    progress_data = {}

    start_time = time.time()

    with tqdm(total=total_ips, desc="Overall Progress", unit="IP") as overall_pbar:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            for ip in ips:
                while not memory_within_limit():
                    time.sleep(1)

                future = executor.submit(process_ip, ip, folder, progress_data)
                futures[future] = ip

            for future in as_completed(futures):
                ip = futures[future]
                overall_pbar.set_postfix_str(f"Current IP: {ip}")
                overall_pbar.update(1)
                try:
                    future.result()
                except Exception as e:
                    progress_data[ip] = f"Exception: {e}"

    end_time = time.time()
    elapsed_time = end_time - start_time

    screenshot_count = sum(1 for status in progress_data.values() if status == "Success")
    failed_ips = [ip for ip, status in progress_data.items() if status != "Success"]

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
