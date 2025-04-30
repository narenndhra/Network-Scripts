import subprocess
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import textwrap
import time
from PIL import Image, ImageDraw, ImageFont

# Function to strip ANSI escape codes
def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)

# Run sslscan command
def run_sslscan(ip):
    command = f"sslscan {ip}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    clean_output = strip_ansi_codes(result.stdout)
    return command, clean_output

# Save output to images with dynamically adjusted height and minimal margin
def save_output_to_images(ip, command, output, folder):
    # Define image properties
    image_width = 1024  # Fixed width
    background_color = "#0C0C0C"
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
    font_size = 16
    font = ImageFont.truetype(font_path, font_size)
    
    # Define color grading
    text_color = "#C0C0C0"
    key_color = "#61AFEF"
    command_color = "#FF0000"
    highlight_color = "#61AFEF"  # Blue color for key highlights
    tls_protocols_color = "#FF4500"  # Red color for SSL/TLS Protocols section
    red_rectangle_color = "#FF0000"  # Red color for rectangle highlights

    line_height = font_size + 6
    max_lines_per_image = 50  # Define the maximum number of lines per image
    output_lines = output.splitlines()

    # Define the list of key-value pairs to highlight
    highlight_keys = [
        "not valid before", "not valid after", "subject", "issuer",
        "signature algorithm", "rsa key strength", "ssl/tls protocols"
    ]

    # Wrap lines that are too long
    wrapped_lines = []
    for line in output_lines:
        wrapped_lines.extend(textwrap.wrap(line, width=118) if len(line) > 118 else [line])

    wrapped_lines.insert(0, f"Command: {command}")  # Add command as the first line

    # Split into chunks based on max lines per image
    chunks = [wrapped_lines[i:i + max_lines_per_image] for i in range(0, len(wrapped_lines), max_lines_per_image)]
    image_files = []

    for index, chunk in enumerate(chunks):
        # Calculate required image height
        required_height = len(chunk) * line_height + 20  # Minimal margin
        img = Image.new("RGB", (image_width, required_height), color=background_color)
        draw = ImageDraw.Draw(img)

        y_position = 10
        for line in chunk:
            if "Command:" in line:
                draw.text((10, y_position), line, font=font, fill=command_color)
            else:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    key_highlight = key.lower() in highlight_keys

                    if key_highlight:
                        # Draw red rectangle around the entire key-value pair
                        key_value_text = f"{key}: {value}"
                        key_value_position = (10, y_position)
                        key_value_size = draw.textbbox((0, 0), key_value_text, font=font)
                        rectangle_bbox = (key_value_position[0] - 2, key_value_position[1] - 2, key_value_position[0] + key_value_size[2] + 2, key_value_position[1] + key_value_size[3] + 2)
                        draw.rectangle(rectangle_bbox, outline=red_rectangle_color)
                        draw.text(key_value_position, key_value_text, font=font, fill=text_color)
                    else:
                        draw.text((10, y_position), key + ":", font=font, fill=key_color)
                        draw.text((10 + draw.textbbox((0, 0), key + ":", font=font)[2], y_position), value, font=font, fill=text_color)
                else:
                    if "SSL/TLS Protocols" in line:
                        # Highlight "SSL/TLS Protocols" section in red
                        section_title = "SSL/TLS Protocols"
                        draw.text((10, y_position), section_title, font=font, fill=tls_protocols_color)
                        y_position += line_height
                    else:
                        draw.text((10, y_position), line, font=font, fill=text_color)

            y_position += line_height

        # Crop image to content with 1mm margin
        content_bbox = img.getbbox()
        cropped_img = img.crop(content_bbox)
        image_file = os.path.join(folder, f"{ip.replace('.', '_')}_part{index+1}.png")
        cropped_img.save(image_file)
        image_files.append(image_file)

    return image_files

# Process IP function
def process_ip(ip, folder, progress_data):
    try:
        command, output = run_sslscan(ip)
        save_output_to_images(ip, command, output, folder)
        progress_data[ip] = "Success"
    except Exception as e:
        progress_data[ip] = f"Error: {e}"

# Main function
def main():
    with open("ip.txt", "r") as file:
        ips = [line.strip() for line in file]

    folder = "sslscan_results"
    if not os.path.exists(folder):
        os.makedirs(folder)

    total_ips = len(ips)
    progress_data = {}

    start_time = time.time()

    with tqdm(total=total_ips, desc="Overall Progress", unit="IP") as overall_pbar:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(process_ip, ip, folder, progress_data): ip for ip in ips}
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
        print(f"\nIPs with errors or no screenshot: {len(failed_ips)}")
        for ip in failed_ips:
            print(f"{ip}: {progress_data[ip]}")

if __name__ == "__main__":
    main()
