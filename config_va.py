import pandas as pd
import re
from xlsxwriter.utility import xl_col_to_name

# === User Input ===
input_csv = input("Enter full path to the Nessus compliance CSV file: ").strip()

# === Load CSV ===
df = pd.read_csv(input_csv)

# === Filter checklist entries only ===
checklist_rows = df[df['Description'].str.contains(r'^\s*"\d+\.\d+', na=False)]

# === Parsing Logic ===
def extract_fields(row):
    text = row['Description'].strip('"')
    ip = row['Host']
    risk = row.get('Risk', '')

    fields = {
        "IP": ip,
        "Checklist": None,
        "Description": None,
        "Solution": None,
        "Impact": None,
        "Policy Value": None,
        "Actual Value": None,
        "Result": risk,
    }

    # Extract checklist and result status
    checklist_match = re.match(r'^(\d+\.\d+\.\d+.*?)\s*:\s*\[(PASSED|FAILED)\]', text)
    if checklist_match:
        fields["Checklist"] = f'{checklist_match.group(1)} : [{checklist_match.group(2)}]'
        text = text[checklist_match.end():].strip()

    # Split into Description → Solution → Impact
    solution_split = re.split(r'\n\s*Solution:\s*\n', text, maxsplit=1, flags=re.IGNORECASE)
    if len(solution_split) == 2:
        fields["Description"] = solution_split[0].strip()
        impact_split = re.split(r'\n\s*Impact:\s*\n', solution_split[1], maxsplit=1, flags=re.IGNORECASE)
        if len(impact_split) == 2:
            fields["Solution"] = impact_split[0].strip()
            remaining = impact_split[1]
        else:
            fields["Solution"] = solution_split[1].strip()
            remaining = ""
    else:
        fields["Description"] = text.strip()
        remaining = ""

    # Strip "See Also" and "Reference"
    remaining = re.sub(r'See Also:.*', '', remaining, flags=re.DOTALL | re.IGNORECASE)
    remaining = re.sub(r'Reference:.*', '', remaining, flags=re.DOTALL | re.IGNORECASE)

    # Pull Policy and Actual Values from raw full Description
    full_text = row['Description']
    policy_val = re.search(r'Policy Value:\s*([^\n]*)', full_text, re.IGNORECASE)
    actual_val = re.search(r'Actual Value:\s*([^\n]*)', full_text, re.IGNORECASE)
    if policy_val:
        fields["Policy Value"] = policy_val.group(1).strip()
    if actual_val:
        fields["Actual Value"] = actual_val.group(1).strip()

    fields["Impact"] = remaining.strip() if remaining else None
    return fields

# === Apply Parsing ===
parsed_records = checklist_rows.apply(extract_fields, axis=1).tolist()
final_df = pd.DataFrame(parsed_records)

# === Export to Excel ===
output_excel = "compliance_by_ip.xlsx"
with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
    workbook = writer.book
    for ip in final_df['IP'].unique():
        ip_df = final_df[final_df['IP'] == ip].drop(columns=["IP"])
        sheet_name = ip.replace('.', '_')
        ip_df.to_excel(writer, sheet_name=sheet_name, index=False)

        worksheet = writer.sheets[sheet_name]
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
        for col_idx in range(len(ip_df.columns)):
            col_letter = xl_col_to_name(col_idx)
            worksheet.set_column(f'{col_letter}:{col_letter}', 45, wrap_format)

print(f"\n✅ Done! Excel saved as: {output_excel}")
