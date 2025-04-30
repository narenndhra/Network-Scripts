import os
import pandas as pd
from multiprocessing import Pool
from tqdm import tqdm

def process_csv(file_path):
    try:
        # Load the CSV file
        csv_data = pd.read_csv(file_path)
        
        # Filter rows to keep only 'Critical', 'High', 'Medium', 'Low' risk levels
        valid_risks = ['Critical', 'High', 'Medium', 'Low']
        cleaned_data = csv_data[csv_data['Risk'].isin(valid_risks)]
        
        # Create the output file path
        output_file_path = file_path.replace('.csv', '_cleaned.csv')
        
        # Save the cleaned data to a new CSV file
        cleaned_data.to_csv(output_file_path, index=False)
        
        return f"Cleaned data saved to {output_file_path}"
    except Exception as e:
        return f"Failed to process {file_path}: {e}"

def process_files_in_folder(folder_path):
    # List all files in the given folder
    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.endswith('.csv')]
    
    # Use multiprocessing to process files
    with Pool() as pool:
        # Use tqdm to show progress
        results = list(tqdm(pool.imap(process_csv, files), total=len(files)))
    
    # Print the results
    for result in results:
        print(result)

# Specify the folder path
folder_path = '/root/Documents/Checklist/csv'

# Call the function to process the CSV files
process_files_in_folder(folder_path)
